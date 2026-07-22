"""v2.8 — LumenAI OR Connect: Perioperative Coordination Engine tests (Project Symphony)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.inspection import Inspection
from app.models.or_connect import RISK_CRITICAL_FINDING_UNRESOLVED, RISK_VENDOR_TRAY_NOT_RECEIVED, ROLE_SPD, ROLE_SURGEON

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA = "0rc0nnec" + "0" * 56
TENANT = "default-tenant"


def _make_inspection(**overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=TENANT, file_name="x.jpg", instrument_type="scissors",
            has_image=True, image_sha256=SHA, score_status="scored", risk_score=10,
            detected_issue="none", stain_detected=False, supervisor_review_required=False,
            qa_review_status="pending", status="pending", inspected_zones_json="null",
            coverage_pct=90, baseline_status="approved",
        )
        defaults.update(overrides)
        insp = Inspection(**defaults)
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _create_case(scheduled_start=None, **overrides) -> dict:
    payload = {
        "procedure": "Total Knee Replacement", "service_line": "Orthopedics", "surgeon": "Dr. Smith",
        "facility_name": "Mercy General", "operating_room": "OR 4",
        "scheduled_start": (scheduled_start or datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
        "vendor_name": "AcmeSurgical",
    }
    payload.update(overrides)
    r = client.post("/api/or-connect/cases", json=payload, headers=AUTH_MGR)
    assert r.status_code == 201, r.text
    return r.json()


class TestCaseCoordinationEngine:
    def test_create_case_returns_expected_fields(self):
        case = _create_case()
        assert case["procedure"] == "Total Knee Replacement"
        assert case["case_ref"].startswith("CASE-")
        assert case["supervisor_approved"] is False

    def test_case_creation_requires_leadership_role(self):
        r = client.post(
            "/api/or-connect/cases",
            json={"procedure": "x", "scheduled_start": datetime.now(timezone.utc).isoformat()},
            headers=AUTH_VIEWER,
        )
        assert r.status_code == 403

    def test_get_case_detail_includes_digital_twins_and_status(self):
        case = _create_case()
        insp_id = _make_inspection(instrument_barcode="or-connect-001")
        client.post(f"/api/or-connect/cases/{case['id']}/link-inspection?inspection_id={insp_id}", headers=AUTH_OPERATOR)

        r = client.get(f"/api/or-connect/cases/{case['id']}", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        body = r.json()
        assert body["inspection_ids"] == [insp_id]
        assert "barcode:or-connect-001" in body["digital_twins"]
        assert body["inspection_status"] == "complete"

    def test_get_missing_case_404(self):
        r = client.get("/api/or-connect/cases/999999999", headers=AUTH_OPERATOR)
        assert r.status_code == 404

    def test_add_tray_and_update_status(self):
        case = _create_case()
        r = client.post(
            f"/api/or-connect/cases/{case['id']}/trays",
            json={"tray_name": "Spine Set A", "vendor_name": "AcmeSurgical"}, headers=AUTH_OPERATOR,
        )
        assert r.status_code == 201
        tray = r.json()
        assert tray["status"] == "requested"

        r2 = client.patch(f"/api/or-connect/trays/{tray['id']}", json={"status": "received"}, headers=AUTH_OPERATOR)
        assert r2.status_code == 200
        assert r2.json()["status"] == "received"
        assert r2.json()["received_at"] is not None


class TestCaseReadinessScore:
    def test_score_is_100_when_everything_complete(self):
        case = _create_case()
        insp_id = _make_inspection(coverage_pct=100)
        client.post(f"/api/or-connect/cases/{case['id']}/link-inspection?inspection_id={insp_id}", headers=AUTH_OPERATOR)
        client.post(f"/api/or-connect/cases/{case['id']}/approve", json={"approved": True}, headers=AUTH_MGR)

        r = client.get(f"/api/or-connect/cases/{case['id']}/readiness-score", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        body = r.json()
        assert body["score"] == 100
        assert "All weighted readiness factors are fully satisfied." in body["rationale"]

    def test_score_drops_with_incomplete_tray(self):
        case = _create_case()
        client.post(
            f"/api/or-connect/cases/{case['id']}/trays",
            json={"tray_name": "Spine Set A", "vendor_name": "AcmeSurgical"}, headers=AUTH_OPERATOR,
        )
        r = client.get(f"/api/or-connect/cases/{case['id']}/readiness-score", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        body = r.json()
        assert body["score"] < 100
        assert "vendor tray arrival" in body["rationale"].lower()

    def test_readiness_score_missing_case_404(self):
        r = client.get("/api/or-connect/cases/999999999/readiness-score", headers=AUTH_OPERATOR)
        assert r.status_code == 404


class TestReadinessTimeline:
    def test_timeline_has_seven_steps(self):
        case = _create_case()
        r = client.get(f"/api/or-connect/cases/{case['id']}/timeline", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        body = r.json()
        step_names = [s["step"] for s in body["steps"]]
        assert step_names == [
            "Case Scheduled", "Vendor Confirmed", "Tray Received", "Inspection Complete",
            "Supervisor Approved", "Packaging", "Ready for OR",
        ]
        assert body["steps"][0]["completed"] is True
        assert body["steps"][0]["timestamp"] is not None

    def test_incomplete_steps_appear_as_blockers(self):
        case = _create_case()
        r = client.get(f"/api/or-connect/cases/{case['id']}/timeline", headers=AUTH_OPERATOR)
        body = r.json()
        assert len(body["blockers"]) > 0
        assert all("step" in b and "reason" in b for b in body["blockers"])


class TestOperationalRiskDetection:
    def test_vendor_tray_not_received_detected_when_case_imminent(self):
        case = _create_case(scheduled_start=datetime.now(timezone.utc) + timedelta(hours=2))
        client.post(
            f"/api/or-connect/cases/{case['id']}/trays",
            json={"tray_name": "Spine Set A", "vendor_name": "AcmeSurgical"}, headers=AUTH_OPERATOR,
        )
        r = client.get(f"/api/or-connect/cases/{case['id']}/risks", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        risk_types = [risk["risk_type"] for risk in r.json()["risks"]]
        assert RISK_VENDOR_TRAY_NOT_RECEIVED in risk_types

    def test_no_risk_when_tray_far_out_and_not_urgent(self):
        case = _create_case(scheduled_start=datetime.now(timezone.utc) + timedelta(days=5))
        client.post(
            f"/api/or-connect/cases/{case['id']}/trays",
            json={"tray_name": "Spine Set A", "vendor_name": "AcmeSurgical"}, headers=AUTH_OPERATOR,
        )
        r = client.get(f"/api/or-connect/cases/{case['id']}/risks", headers=AUTH_OPERATOR)
        risk_types = [risk["risk_type"] for risk in r.json()["risks"]]
        assert RISK_VENDOR_TRAY_NOT_RECEIVED not in risk_types

    def test_critical_finding_unresolved_detected(self):
        case = _create_case()
        insp_id = _make_inspection(
            detected_issue="crack", risk_score=90, recommended_action="Remove from service — crack detected.",
        )
        client.post(f"/api/or-connect/cases/{case['id']}/link-inspection?inspection_id={insp_id}", headers=AUTH_OPERATOR)
        r = client.get(f"/api/or-connect/cases/{case['id']}/risks", headers=AUTH_OPERATOR)
        risk_types = [risk["risk_type"] for risk in r.json()["risks"]]
        assert RISK_CRITICAL_FINDING_UNRESOLVED in risk_types

    def test_risk_detection_missing_case_404(self):
        r = client.get("/api/or-connect/cases/999999999/risks", headers=AUTH_OPERATOR)
        assert r.status_code == 404


class TestStakeholderNotifications:
    def test_generate_notifications_routes_to_correct_roles(self):
        case = _create_case()
        insp_id = _make_inspection(
            detected_issue="crack", risk_score=90, recommended_action="Remove from service — crack detected.",
        )
        client.post(f"/api/or-connect/cases/{case['id']}/link-inspection?inspection_id={insp_id}", headers=AUTH_OPERATOR)

        r = client.post(f"/api/or-connect/cases/{case['id']}/notifications/generate", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        roles = {n["recipient_role"] for n in r.json()["notifications"]}
        assert ROLE_SURGEON in roles
        assert ROLE_SPD in roles

    def test_list_and_mark_read(self):
        case = _create_case()
        insp_id = _make_inspection(
            detected_issue="crack", risk_score=90, recommended_action="Remove from service — crack detected.",
        )
        client.post(f"/api/or-connect/cases/{case['id']}/link-inspection?inspection_id={insp_id}", headers=AUTH_OPERATOR)
        client.post(f"/api/or-connect/cases/{case['id']}/notifications/generate", headers=AUTH_OPERATOR)

        r = client.get("/api/or-connect/notifications", params={"recipient_role": ROLE_SPD}, headers=AUTH_OPERATOR)
        assert r.status_code == 200
        notifications = r.json()["notifications"]
        assert len(notifications) > 0

        notif_id = notifications[0]["id"]
        r2 = client.post(f"/api/or-connect/notifications/{notif_id}/read", headers=AUTH_OPERATOR)
        assert r2.status_code == 200
        assert r2.json()["read"] is True

    def test_invalid_recipient_role_rejected(self):
        r = client.get("/api/or-connect/notifications", params={"recipient_role": "not_a_role"}, headers=AUTH_OPERATOR)
        assert r.status_code == 422


class TestVendorAccessControls:
    def test_vendor_sees_only_own_trays(self):
        case = _create_case(vendor_name="AcmeSurgical")
        client.post(
            f"/api/or-connect/cases/{case['id']}/trays",
            json={"tray_name": "Acme Tray", "vendor_name": "AcmeSurgical"}, headers=AUTH_OPERATOR,
        )
        client.post(
            f"/api/or-connect/cases/{case['id']}/trays",
            json={"tray_name": "Other Vendor Tray", "vendor_name": "OtherVendor"}, headers=AUTH_OPERATOR,
        )

        r = client.get(
            "/api/or-connect/vendor-portal", headers={**AUTH_ADMIN, "X-Manufacturer-ID": "AcmeSurgical"},
        )
        assert r.status_code == 200
        tray_names = [t["tray_name"] for t in r.json()["requested_trays"]]
        assert "Acme Tray" in tray_names
        assert "Other Vendor Tray" not in tray_names

    def test_vendor_cannot_confirm_delivery_for_other_vendors_tray(self):
        case = _create_case()
        tray = client.post(
            f"/api/or-connect/cases/{case['id']}/trays",
            json={"tray_name": "Other Vendor Tray", "vendor_name": "OtherVendor"}, headers=AUTH_OPERATOR,
        ).json()

        r = client.post(
            f"/api/or-connect/vendor-portal/trays/{tray['id']}/confirm-delivery",
            json={"confirmed_by": "Someone"},
            headers={**AUTH_ADMIN, "X-Manufacturer-ID": "AcmeSurgical"},
        )
        assert r.status_code == 403

    def test_vendor_can_confirm_delivery_for_own_tray(self):
        case = _create_case()
        tray = client.post(
            f"/api/or-connect/cases/{case['id']}/trays",
            json={"tray_name": "Acme Tray", "vendor_name": "AcmeSurgical"}, headers=AUTH_OPERATOR,
        ).json()

        r = client.post(
            f"/api/or-connect/vendor-portal/trays/{tray['id']}/confirm-delivery",
            json={"confirmed_by": "Driver Joe"},
            headers={**AUTH_ADMIN, "X-Manufacturer-ID": "AcmeSurgical"},
        )
        assert r.status_code == 200
        assert r.json()["delivery_confirmed_by"] == "Driver Joe"

    def test_vendor_portal_requires_manufacturer_header(self):
        r = client.get("/api/or-connect/vendor-portal", headers=AUTH_ADMIN)
        assert r.status_code == 403

    def test_vendor_can_request_replacement_for_own_tray(self):
        case = _create_case()
        tray = client.post(
            f"/api/or-connect/cases/{case['id']}/trays",
            json={"tray_name": "Acme Tray", "vendor_name": "AcmeSurgical"}, headers=AUTH_OPERATOR,
        ).json()

        r = client.post(
            f"/api/or-connect/vendor-portal/trays/{tray['id']}/request-replacement",
            json={"notes": "Damaged in transit"},
            headers={**AUTH_ADMIN, "X-Manufacturer-ID": "AcmeSurgical"},
        )
        assert r.status_code == 200
        assert r.json()["replacement_requested"] is True


class TestRepairIntegration:
    def test_create_and_update_repair_request(self):
        case = _create_case()
        insp_id = _make_inspection(instrument_barcode="repair-001")

        r = client.post(
            "/api/or-connect/repairs",
            json={"inspection_id": insp_id, "case_id": case["id"], "vendor_name": "AcmeSurgical", "repair_type": "recoat"},
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 201
        repair = r.json()
        assert repair["status"] == "pending"
        assert repair["instrument_identity"] == "barcode:repair-001"

        r2 = client.patch(f"/api/or-connect/repairs/{repair['id']}", json={"status": "returned"}, headers=AUTH_MGR)
        assert r2.status_code == 200
        assert r2.json()["status"] == "returned"

    def test_repair_incomplete_risk_and_repair_completion_factor(self):
        case = _create_case()
        insp_id = _make_inspection(instrument_barcode="repair-002")
        client.post(f"/api/or-connect/cases/{case['id']}/link-inspection?inspection_id={insp_id}", headers=AUTH_OPERATOR)
        client.post(
            "/api/or-connect/repairs",
            json={"inspection_id": insp_id, "case_id": case["id"]}, headers=AUTH_OPERATOR,
        )

        r = client.get(f"/api/or-connect/cases/{case['id']}/readiness-score", headers=AUTH_OPERATOR)
        assert r.json()["factors"]["repair_completion"]["value"] == 0.0

        r2 = client.get(f"/api/or-connect/cases/{case['id']}/risks", headers=AUTH_OPERATOR)
        risk_types = [risk["risk_type"] for risk in r2.json()["risks"]]
        assert "repair_incomplete" in risk_types

    def test_clinical_engineering_summary(self):
        case = _create_case()
        insp_id = _make_inspection(instrument_barcode="repair-003")
        client.post(
            "/api/or-connect/repairs",
            json={"inspection_id": insp_id, "case_id": case["id"]}, headers=AUTH_OPERATOR,
        )
        r = client.get("/api/or-connect/clinical-engineering", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert r.json()["total_repairs"] >= 1


class TestCaseIntelligenceDashboard:
    def test_dashboard_returns_todays_cases(self):
        scheduled = datetime.now(timezone.utc) + timedelta(hours=1)
        case = _create_case(scheduled_start=scheduled)
        # Pin the dashboard's date window to the case's own scheduled UTC date.
        # Requesting the bare endpoint would default the window to "now's" UTC
        # date, so a case at now+1h that crosses into the next UTC day (suite
        # running in the last hour before midnight) would fall outside "today"
        # and the count would be 0 — a real UTC-midnight flake. Pinning the
        # target_date to the case's date removes all clock dependence.
        target_date = scheduled.date().isoformat()
        r = client.get(
            f"/api/or-connect/dashboard?target_date={target_date}", headers=AUTH_OPERATOR
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total_cases"] >= 1
        assert any(c["case_ref"] == case["case_ref"] for c in body["cases"])
        assert "vendor_tray_status" in body
        assert "outstanding_blockers" in body

    def test_dashboard_unauthenticated_rejected(self):
        r = client.get("/api/or-connect/dashboard")
        assert r.status_code in (401, 403)


class TestExecutiveDashboard:
    def test_executive_dashboard_shape(self):
        case = _create_case()
        client.get(f"/api/or-connect/cases/{case['id']}/readiness-score", headers=AUTH_OPERATOR)
        r = client.get("/api/or-connect/executive-dashboard", headers=AUTH_MGR)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "case_readiness_trend", "delay_causes", "vendor_performance",
            "inspection_turnaround_hours", "repair_impact", "quality_alerts", "operational_bottlenecks",
        ):
            assert key in body

    def test_executive_dashboard_requires_leadership_role(self):
        r = client.get("/api/or-connect/executive-dashboard", headers=AUTH_VIEWER)
        assert r.status_code == 403
