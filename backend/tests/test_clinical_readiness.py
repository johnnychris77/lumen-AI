"""v1.6 — Clinical Service Readiness & Instrument Disposition Intelligence."""
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.baseline_library import BaselineLibraryEntry
from app.services.disposition_engine import (
    MANUFACTURER_EVALUATION,
    PROCEED_TO_PACKAGING,
    RECLEAN,
    REMOVE_FROM_SERVICE,
    REPAIR_EVALUATION,
    REPEAT_INSPECTION,
    recommend_disposition,
)
from app.services.readiness_engine import (
    PENDING_SUPERVISOR_REVIEW,
    READY,
    READY_WITH_SUPERVISOR_APPROVAL,
    REMOVE_FROM_SERVICE_STATUS,
    REQUIRES_RECLEANING_STATUS,
    compute_readiness,
)
from app.services.risk_stratification_service import CRITICAL, LOW, stratify_risk

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
SHA = "a1b2c3d4" + "0" * 56
TENANT = "default-tenant"


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"cr-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _create(itype, declared=None, headers=None):
    _baseline(itype)
    r = client.post("/api/inspections", json={
        "instrument_type": itype, "site_name": "Mercy",
        "has_image": True, "image_sha256": SHA, "file_name": "x.jpg",
        "finding_categories": declared or [],
    }, headers=headers or AUTH_OPERATOR)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _get_inspection(iid):
    from app.db import models
    db = SessionLocal()
    try:
        return db.query(models.Inspection).filter(models.Inspection.id == iid).first()
    finally:
        db.close()


class TestReadinessScoreCalculation:
    def test_readiness_score_calculation(self):
        iid = _create("scissors")
        db = SessionLocal()
        try:
            insp = _get_inspection(iid)
            readiness = compute_readiness(db, TENANT, insp, confirmed=False)
            assert readiness["readiness_score"] is None or 0 <= readiness["readiness_score"] <= 100
            # PENDING_SUPERVISOR_REVIEW is the safe, expected outcome for the
            # new AI-analysis-unavailable disposition (no declared findings,
            # no eligible model): classify_readiness()'s existing "unrecognized
            # text — fail safe to human review" branch routes it here.
            assert readiness["status"] in (
                READY, READY_WITH_SUPERVISOR_APPROVAL, REQUIRES_RECLEANING_STATUS,
                PENDING_SUPERVISOR_REVIEW,
            )
        finally:
            db.close()

    def test_confirmed_ready_gets_supervisor_approval_status(self):
        iid = _create("forceps")
        client.post(
            f"/api/inspections/{iid}/supervisor-review",
            json={"agreement": "agree"}, headers=AUTH_MGR,
        )
        db = SessionLocal()
        try:
            insp = _get_inspection(iid)
            readiness = compute_readiness(db, TENANT, insp, confirmed=True)
            if readiness["status"] in (READY, READY_WITH_SUPERVISOR_APPROVAL):
                assert readiness["status"] == READY_WITH_SUPERVISOR_APPROVAL
        finally:
            db.close()

    def test_readiness_via_api(self):
        iid = _create("needle_holder")
        r = client.get(f"/api/inspections/{iid}/evidence-panel", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert "readiness_score" in body
        assert "readiness_status" in body


class TestDispositionRecommendation:
    def test_disposition_recommendation_generation(self):
        iid = _create("scissors", declared=["blood"])
        r = client.get(f"/api/inspections/{iid}/evidence-panel", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["recommended_disposition"]
        assert body["clinical_rationale"]

    def test_every_disposition_has_explanation(self):
        readiness = {"status": REMOVE_FROM_SERVICE_STATUS, "repair_history": False}

        class FakeInsp:
            detected_issue = "crack"
            coverage_pct = 90

        d = recommend_disposition(readiness, FakeInsp(), coverage_pct=90)
        assert d["disposition"] == REMOVE_FROM_SERVICE
        assert d["explanation"]

    def test_low_coverage_recommends_repeat_inspection(self):
        readiness = {"status": READY, "repair_history": False}

        class FakeInsp:
            detected_issue = "none"

        d = recommend_disposition(readiness, FakeInsp(), coverage_pct=30)
        assert d["disposition"] == REPEAT_INSPECTION

    def test_recurring_manufacturer_attributable_condition(self):
        readiness = {"status": "Requires Repair", "repair_history": True}

        class FakeInsp:
            detected_issue = "corrosion"

        d = recommend_disposition(readiness, FakeInsp(), coverage_pct=90)
        assert d["disposition"] == MANUFACTURER_EVALUATION

    def test_ready_with_approval_proceeds_to_packaging(self):
        readiness = {"status": READY_WITH_SUPERVISOR_APPROVAL, "repair_history": False}

        class FakeInsp:
            detected_issue = "none"

        d = recommend_disposition(readiness, FakeInsp(), coverage_pct=100)
        assert d["disposition"] == PROCEED_TO_PACKAGING

    def test_requires_repair_without_history_is_repair_evaluation(self):
        readiness = {"status": "Requires Repair", "repair_history": False}

        class FakeInsp:
            detected_issue = "crack"

        d = recommend_disposition(readiness, FakeInsp(), coverage_pct=90)
        assert d["disposition"] == REPAIR_EVALUATION

    def test_reclean_disposition(self):
        readiness = {"status": REQUIRES_RECLEANING_STATUS, "repair_history": False}

        class FakeInsp:
            detected_issue = "blood"

        d = recommend_disposition(readiness, FakeInsp(), coverage_pct=90)
        assert d["disposition"] == RECLEAN


class TestSupervisorDispositionWorkspace:
    def test_supervisor_override_requires_reason(self):
        iid = _create("scissors")
        r = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "reclean", "ai_recommended_disposition": "Proceed to Packaging"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 422

    def test_supervisor_override_with_reason_succeeds(self):
        iid = _create("scissors")
        r = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={
                "action": "reclean", "ai_recommended_disposition": "Proceed to Packaging",
                "reason": "Residual debris still visible in hinge.",
            },
            headers=AUTH_MGR,
        )
        assert r.status_code == 201, r.text

    def test_approve_does_not_require_reason(self):
        iid = _create("scissors")
        r = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "approve", "ai_recommended_disposition": "Proceed to Packaging"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 201, r.text

    def test_invalid_action_rejected(self):
        iid = _create("scissors")
        r = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "not_a_real_action", "reason": "x"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 422

    def test_operator_cannot_submit_disposition_action(self):
        iid = _create("scissors")
        r = client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "approve"}, headers=AUTH_OPERATOR,
        )
        assert r.status_code == 403

    def test_disposition_action_history_listed(self):
        iid = _create("forceps")
        client.post(
            f"/api/inspections/{iid}/disposition-action",
            json={"action": "escalate", "reason": "Needs director review."},
            headers=AUTH_MGR,
        )
        r = client.get(f"/api/inspections/{iid}/disposition-actions", headers=AUTH_ADMIN)
        assert r.status_code == 200
        assert any(a["action"] == "escalate" for a in r.json()["actions"])


class TestReadinessDashboard:
    def test_readiness_dashboard_aggregation(self):
        _create("scissors")
        r = client.get("/api/clinical-readiness/dashboard", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "ready_for_packaging", "requires_recleaning", "requires_repair",
            "remove_from_service", "supervisor_pending", "average_readiness_score",
            "disposition_trends", "total_inspections",
        ):
            assert key in body

    def test_enterprise_analytics_leadership_only(self):
        _create("scissors")
        r = client.get("/api/clinical-readiness/enterprise-analytics", headers=AUTH_OPERATOR)
        assert r.status_code == 403
        r2 = client.get("/api/clinical-readiness/enterprise-analytics", headers=AUTH_MGR)
        assert r2.status_code == 200
        body = r2.json()
        for key in (
            "readiness_trends", "disposition_distribution", "supervisor_overrides",
            "repair_referrals", "high_risk_instrument_families", "most_common_disposition_reasons",
        ):
            assert key in body


class TestReadinessTimeline:
    def test_timeline_completeness(self):
        iid = _create("needle_holder")
        r = client.get(f"/api/inspections/{iid}/readiness-timeline", headers=AUTH_ADMIN)
        assert r.status_code == 200
        steps = r.json()["steps"]
        step_names = [s["step"] for s in steps]
        assert step_names == [
            "Image Uploaded", "Instrument Identified", "Coverage Completed",
            "AI Findings", "Clinical Reasoning", "Supervisor Review",
            "Disposition", "Ready for Packaging",
        ]
        assert steps[0]["completed"] is True  # image uploaded
        assert steps[5]["completed"] is False  # no supervisor review yet

    def test_timeline_reflects_supervisor_review(self):
        iid = _create("needle_holder")
        client.post(
            f"/api/inspections/{iid}/supervisor-review",
            json={"agreement": "agree"}, headers=AUTH_MGR,
        )
        r = client.get(f"/api/inspections/{iid}/readiness-timeline", headers=AUTH_ADMIN)
        steps = r.json()["steps"]
        review_step = next(s for s in steps if s["step"] == "Supervisor Review")
        assert review_step["completed"] is True
        assert review_step["timestamp"] is not None


class TestRiskStratification:
    def test_risk_stratification_logic(self):
        db = SessionLocal()
        try:
            class FakeInspLow:
                detected_issue = "none"
                disposition = "PASS"
                coverage_pct = 100
                baseline_status = "approved_baseline_found"

            result = stratify_risk(FakeInspLow())
            assert result["risk_tier"] == LOW

            class FakeInspCritical:
                detected_issue = "crack"
                disposition = "REMOVE FROM SERVICE"
                coverage_pct = 20
                baseline_status = "no_approved_baseline"

            result2 = stratify_risk(FakeInspCritical(), high_risk_zone_finding=True)
            assert result2["risk_tier"] == CRITICAL
            assert result2["reasons"]
        finally:
            db.close()

    def test_risk_stratification_via_api(self):
        iid = _create("scissors")
        r = client.get(f"/api/inspections/{iid}/risk-stratification", headers=AUTH_ADMIN)
        assert r.status_code == 200
        assert r.json()["risk_tier"] in ("Low Risk", "Moderate Risk", "High Risk", "Critical")


class TestExportReport:
    def test_export_report_generation_json(self):
        iid = _create("scissors")
        r = client.get(f"/api/inspections/{iid}/readiness-report", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert "instrument" in body
        assert "evidence" in body
        assert "timeline" in body
        assert "risk_stratification" in body
        assert "audit_metadata" in body

    def test_export_report_generation_pdf(self):
        iid = _create("forceps")
        r = client.get(f"/api/inspections/{iid}/readiness-report.pdf", headers=AUTH_ADMIN)
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert len(r.content) > 100


class TestInstrumentConditionTracker:
    def test_condition_tracker_no_history_for_untracked(self):
        r = client.get(
            "/api/clinical-readiness/instrument-condition",
            params={"instrument_identity": "barcode:NOT-REAL-000"},
            headers=AUTH_ADMIN,
        )
        assert r.status_code == 404
