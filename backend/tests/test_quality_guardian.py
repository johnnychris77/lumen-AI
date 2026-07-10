"""v2.9 — LumenAI Quality: Closed-Loop Quality Intelligence tests (Project Guardian)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.competency_event import CompetencyEvent
from app.models.inspection import Inspection
from app.models.or_connect import SurgicalCase, VendorTray
from app.services.quality_event_service import classify_narrative

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA = "gu4rd1an" + "0" * 56
TENANT = "default-tenant"


def _make_inspection(**overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=TENANT, file_name="x.jpg", instrument_type="yankauer_suction",
            has_image=True, image_sha256=SHA, score_status="scored", risk_score=10,
            detected_issue="none", stain_detected=False, supervisor_review_required=False,
            qa_review_status="pending", status="pending", inspected_zones_json="null",
            coverage_pct=100, baseline_status="approved", disposition="PASS", technician="Alex Tech",
            facility_name="Mercy General", department="Ortho",
        )
        defaults.update(overrides)
        insp = Inspection(**defaults)
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


def _make_case(**overrides) -> int:
    db = SessionLocal()
    try:
        defaults = dict(
            tenant_id=TENANT, case_ref=f"CASE-TEST-{datetime.now(timezone.utc).timestamp()}",
            procedure="Total Knee Replacement", service_line="Orthopedics", surgeon="Dr. Smith",
            facility_name="Mercy General", operating_room="OR 4",
            scheduled_start=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        defaults.update(overrides)
        case = SurgicalCase(**defaults)
        db.add(case)
        db.commit()
        db.refresh(case)
        return case.id
    finally:
        db.close()


def _link_inspection_to_case(inspection_id: int, case_id: int) -> None:
    db = SessionLocal()
    try:
        insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
        insp.case_id = case_id
        db.commit()
    finally:
        db.close()


def _create_event(**overrides) -> dict:
    payload = {
        "event_date": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "narrative": "Dirty suction found in OR, visible blood residue on Yankauer tip.",
        "source_system": "manual", "facility_name": "Mercy General", "severity": "high",
    }
    payload.update(overrides)
    r = client.post("/api/quality-guardian/events", json=payload, headers=AUTH_OPERATOR)
    assert r.status_code == 201, r.text
    return r.json()


class TestNarrativeClassification:
    def test_classify_blood_and_instrument(self):
        result = classify_narrative("Dirty suction found in OR, visible blood residue on Yankauer tip.")
        assert result["instrument_type_guess"] == "yankauer_suction"
        assert result["finding_type"] == "blood"
        assert result["spd_category"] == "organic_residue"
        assert result["risk_level"] == "high"
        assert result["confidence"] == 0.98
        assert result["requires_supervisor_classification"] is False

    def test_classify_unrecognized_narrative_requires_supervisor(self):
        result = classify_narrative("Something seemed off but nobody could describe it.")
        assert result["finding_type"] == "unknown"
        assert result["requires_supervisor_classification"] is True

    def test_narrative_preserved_alongside_classification(self):
        narrative = "Wrapper tear noted on tray at case start."
        event = _create_event(narrative=narrative)
        assert event["narrative"] == narrative
        assert event["finding_type"] == "wrapper_tear"
        assert event["spd_category"] == "packaging"

    def test_event_creation_requires_valid_source_system(self):
        r = client.post(
            "/api/quality-guardian/events",
            json={"event_date": datetime.now(timezone.utc).isoformat(), "narrative": "x", "source_system": "not_real"},
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 422

    def test_reclassify_endpoint(self):
        event = _create_event(narrative="No recognizable keywords here at all.")
        assert event["finding_type"] == "unknown"
        r = client.post(f"/api/quality-guardian/events/{event['id']}/classify", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert r.json()["finding_type"] == "unknown"


class TestTaxonomyMapping:
    def test_default_taxonomy_has_all_categories(self):
        r = client.get("/api/quality-guardian/taxonomy", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        taxonomy = r.json()["taxonomy"]
        assert set(taxonomy) == {
            "organic_residue", "instrument_condition", "assembly", "packaging",
            "sterilization_indicators", "unknown",
        }
        organic_terms = {t["term"] for t in taxonomy["organic_residue"]}
        assert organic_terms == {"blood", "bone", "tissue", "protein", "debris"}

    def test_add_custom_taxonomy_term(self):
        r = client.post(
            "/api/quality-guardian/taxonomy",
            json={"category": "packaging", "term": "seal_failure"}, headers=AUTH_MGR,
        )
        assert r.status_code == 201
        assert r.json()["term"] == "seal_failure"

        r2 = client.get("/api/quality-guardian/taxonomy", headers=AUTH_OPERATOR)
        packaging_terms = {t["term"] for t in r2.json()["taxonomy"]["packaging"]}
        assert "seal_failure" in packaging_terms


class TestEventCorrelation:
    def test_correlates_case_tray_inspection_technician(self):
        case_id = _make_case()
        insp_id = _make_inspection(instrument_barcode="corr-001")
        _link_inspection_to_case(insp_id, case_id)
        db = SessionLocal()
        try:
            db.add(VendorTray(tenant_id=TENANT, case_id=case_id, tray_name="Ortho Set", vendor_name="AcmeSurgical"))
            db.commit()
        finally:
            db.close()

        event = _create_event(case_id=case_id)
        r = client.post(f"/api/quality-guardian/events/{event['id']}/correlate", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        correlations = {c["target_type"]: c for c in r.json()["correlations"]}

        assert correlations["case"]["target_id"] == str(case_id)
        assert correlations["case"]["confidence"] == 1.0
        assert correlations["tray"]["confidence"] > 0
        assert correlations["inspection"]["target_id"] == str(insp_id)
        assert correlations["technician"]["target_id"] == "Alex Tech"
        assert correlations["digital_twin"]["target_id"] == "barcode:corr-001"

    def test_untracked_targets_recorded_honestly(self):
        event = _create_event()
        r = client.post(f"/api/quality-guardian/events/{event['id']}/correlate", headers=AUTH_OPERATOR)
        correlations = {c["target_type"]: c for c in r.json()["correlations"]}
        for target in ("shift", "washer", "inspection_session"):
            assert correlations[target]["tracked"] is False
            assert correlations[target]["confidence"] == 0.0
            assert "does not persist" in correlations[target]["note"]

    def test_confirm_correlation(self):
        case_id = _make_case()
        event = _create_event(case_id=case_id)
        client.post(f"/api/quality-guardian/events/{event['id']}/correlate", headers=AUTH_OPERATOR)
        r = client.get(f"/api/quality-guardian/events/{event['id']}/correlations", headers=AUTH_OPERATOR)
        case_corr_id = next(c["id"] for c in r.json()["correlations"] if c["target_type"] == "case")

        r2 = client.post(
            f"/api/quality-guardian/correlations/{case_corr_id}/confirm",
            json={"confirmed_by": "supervisor@example.com"}, headers=AUTH_MGR,
        )
        assert r2.status_code == 200
        assert r2.json()["supervisor_confirmed"] is True


class TestRCAGeneration:
    def test_generate_draft_has_evidence_and_questions(self):
        case_id = _make_case()
        insp_id = _make_inspection(instrument_barcode="rca-001")
        _link_inspection_to_case(insp_id, case_id)
        event = _create_event(case_id=case_id)

        r = client.post(f"/api/quality-guardian/events/{event['id']}/rca-draft", headers=AUTH_OPERATOR)
        assert r.status_code == 201
        draft = r.json()
        assert draft["likely_process_stage"] == "Manual Cleaning"
        assert len(draft["evidence"]) > 0
        assert len(draft["investigation_questions"]) > 0
        assert draft["inspection_id"] == insp_id

    def test_approve_draft_creates_root_cause_assignment(self):
        case_id = _make_case()
        insp_id = _make_inspection(instrument_barcode="rca-002")
        _link_inspection_to_case(insp_id, case_id)
        event = _create_event(case_id=case_id)
        draft = client.post(f"/api/quality-guardian/events/{event['id']}/rca-draft", headers=AUTH_OPERATOR).json()

        r = client.post(
            f"/api/quality-guardian/rca-drafts/{draft['id']}/approve",
            json={"root_cause": "incomplete_manual_cleaning", "approved_by": "supervisor@example.com"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "approved"
        assert body["root_cause_assignment_id"] is not None

    def test_approve_without_correlated_inspection_rejected(self):
        # No instrument keyword in the narrative, so no case/inspection can
        # even be fuzzy-matched (avoids incidentally matching another test's
        # inspection by instrument type + time window).
        event = _create_event(narrative="Missing lock noted on tray at case start.", facility_name="No Such Facility")
        draft = client.post(f"/api/quality-guardian/events/{event['id']}/rca-draft", headers=AUTH_OPERATOR).json()
        assert draft["inspection_id"] is None

        r = client.post(
            f"/api/quality-guardian/rca-drafts/{draft['id']}/approve",
            json={"root_cause": "unknown"}, headers=AUTH_MGR,
        )
        assert r.status_code == 422

    def test_reject_draft(self):
        event = _create_event()
        draft = client.post(f"/api/quality-guardian/events/{event['id']}/rca-draft", headers=AUTH_OPERATOR).json()
        r = client.post(
            f"/api/quality-guardian/rca-drafts/{draft['id']}/reject",
            json={"rejected_by": "mgr@example.com", "reason": "Insufficient evidence"}, headers=AUTH_MGR,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_supervisor_edit_persisted(self):
        event = _create_event()
        draft = client.post(f"/api/quality-guardian/events/{event['id']}/rca-draft", headers=AUTH_OPERATOR).json()
        r = client.patch(
            f"/api/quality-guardian/rca-drafts/{draft['id']}",
            json={"supervisor_edits": "Confirmed with OR charge nurse."}, headers=AUTH_MGR,
        )
        assert r.status_code == 200
        assert r.json()["supervisor_edits"] == "Confirmed with OR charge nurse."


class TestCapaLifecycle:
    def test_generate_and_accept_recommendation_creates_capa(self):
        event = _create_event()  # organic_residue / blood
        r = client.post(
            "/api/quality-guardian/capa-recommendations/generate", json={"event_id": event["id"]}, headers=AUTH_OPERATOR,
        )
        assert r.status_code == 201
        recs = r.json()["recommendations"]
        assert any(rec["recommendation_type"] == "education" for rec in recs)

        rec_id = recs[0]["id"]
        r2 = client.post(
            f"/api/quality-guardian/capa-recommendations/{rec_id}/accept",
            json={"title": "Cleaning refresher", "owner": "spd_manager@example.com"}, headers=AUTH_MGR,
        )
        assert r2.status_code == 200
        body = r2.json()
        assert body["status"] == "accepted"
        assert body["capa"]["lifecycle_status"] == "open"

    def test_dismiss_recommendation(self):
        event = _create_event()
        recs = client.post(
            "/api/quality-guardian/capa-recommendations/generate", json={"event_id": event["id"]}, headers=AUTH_OPERATOR,
        ).json()["recommendations"]
        r = client.post(f"/api/quality-guardian/capa-recommendations/{recs[0]['id']}/dismiss", headers=AUTH_MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "dismissed"

    def test_full_lifecycle_transitions(self):
        event = _create_event()
        recs = client.post(
            "/api/quality-guardian/capa-recommendations/generate", json={"event_id": event["id"]}, headers=AUTH_OPERATOR,
        ).json()["recommendations"]
        accepted = client.post(
            f"/api/quality-guardian/capa-recommendations/{recs[0]['id']}/accept",
            json={"title": "Test CAPA", "owner": "someone@example.com"}, headers=AUTH_MGR,
        ).json()
        capa_id = accepted["capa"]["id"]

        r1 = client.post(f"/api/quality-guardian/capas/{capa_id}/advance", json={"new_status": "assigned"}, headers=AUTH_MGR)
        assert r1.status_code == 200
        assert r1.json()["lifecycle_status"] == "assigned"

        r2 = client.post(f"/api/quality-guardian/capas/{capa_id}/advance", json={"new_status": "in_progress"}, headers=AUTH_MGR)
        assert r2.json()["lifecycle_status"] == "in_progress"

        r3 = client.post(f"/api/quality-guardian/capas/{capa_id}/advance", json={"new_status": "verified"}, headers=AUTH_MGR)
        assert r3.json()["lifecycle_status"] == "verified"

        r4 = client.post(f"/api/quality-guardian/capas/{capa_id}/advance", json={"new_status": "closed"}, headers=AUTH_MGR)
        assert r4.json()["lifecycle_status"] == "closed"

    def test_invalid_lifecycle_transition_rejected(self):
        event = _create_event()
        recs = client.post(
            "/api/quality-guardian/capa-recommendations/generate", json={"event_id": event["id"]}, headers=AUTH_OPERATOR,
        ).json()["recommendations"]
        accepted = client.post(
            f"/api/quality-guardian/capa-recommendations/{recs[0]['id']}/accept",
            json={"title": "Test CAPA 2", "owner": "someone@example.com"}, headers=AUTH_MGR,
        ).json()
        capa_id = accepted["capa"]["id"]

        r = client.post(f"/api/quality-guardian/capas/{capa_id}/advance", json={"new_status": "verified"}, headers=AUTH_MGR)
        assert r.status_code == 422

    def test_list_capas(self):
        r = client.get("/api/quality-guardian/capas", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert isinstance(r.json()["capas"], list)


class TestCompetencyUpdate:
    def _seed_repeated_errors(self, technician: str, finding_type: str, count: int) -> None:
        db = SessionLocal()
        try:
            for _ in range(count):
                db.add(CompetencyEvent(tenant_id=TENANT, technician=technician, event_type="repeated_error", finding_type=finding_type))
            db.commit()
        finally:
            db.close()

    def test_detects_individual_coaching_opportunity(self):
        self._seed_repeated_errors("Jordan Tech", "blood", 2)
        r = client.post("/api/quality-guardian/competency-opportunities/detect", headers=AUTH_MGR)
        assert r.status_code == 200
        opportunities = r.json()["opportunities"]
        assert any(o["opportunity_type"] == "coaching" and o["scope_value"] == "Jordan Tech" for o in opportunities)

    def test_detects_team_education_opportunity(self):
        for tech in ("Tech A", "Tech B", "Tech C"):
            self._seed_repeated_errors(tech, "corrosion", 2)
        r = client.post("/api/quality-guardian/competency-opportunities/detect", headers=AUTH_MGR)
        opportunities = r.json()["opportunities"]
        assert any(o["opportunity_type"] == "team_education" and o["finding_type"] == "corrosion" for o in opportunities)

    def test_mark_addressed_and_effectiveness(self):
        self._seed_repeated_errors("Casey Tech", "wear", 2)
        opportunities = client.post("/api/quality-guardian/competency-opportunities/detect", headers=AUTH_MGR).json()["opportunities"]
        opp = next(o for o in opportunities if o["scope_value"] == "Casey Tech" and o["finding_type"] == "wear")

        r = client.post(f"/api/quality-guardian/competency-opportunities/{opp['id']}/address", headers=AUTH_MGR)
        assert r.status_code == 200
        assert r.json()["status"] == "addressed"

        r2 = client.get(f"/api/quality-guardian/competency-opportunities/{opp['id']}/effectiveness", headers=AUTH_MGR)
        assert r2.status_code == 200
        assert "effectiveness_score" in r2.json()

    def test_list_opportunities_requires_leadership_role(self):
        r = client.get("/api/quality-guardian/competency-opportunities", headers=AUTH_VIEWER)
        assert r.status_code == 403


class TestFirstPassYield:
    def test_false_pass_detected_from_confirmed_correlated_event(self):
        insp_id = _make_inspection(disposition="PASS", instrument_barcode="fpy-001", facility_name="FPY Facility")
        event = _create_event(narrative="Blood found on suction after case.", facility_name="FPY Facility")

        db = SessionLocal()
        try:
            from app.models.quality_guardian import EventCorrelation

            db.add(EventCorrelation(
                tenant_id=TENANT, event_id=event["id"], target_type="inspection", target_id=str(insp_id),
                confidence=0.9, supervisor_confirmed=True,
            ))
            db.commit()
        finally:
            db.close()

        client.post(f"/api/quality-guardian/events/{event['id']}/confirm", json={}, headers=AUTH_MGR)

        r = client.get(
            "/api/quality-guardian/first-pass-yield", params={"scope_type": "facility", "scope_value": "FPY Facility"},
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total_pass_count"] >= 1
        assert body["confirmed_miss_count"] >= 1
        assert body["false_pass_pct"] > 0

    def test_true_first_pass_when_no_confirmed_event(self):
        _make_inspection(disposition="PASS", facility_name="Clean Facility")
        r = client.get(
            "/api/quality-guardian/first-pass-yield", params={"scope_type": "facility", "scope_value": "Clean Facility"},
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["true_fpy_pct"] == 100.0
        assert body["confirmed_miss_count"] == 0

    def test_invalid_scope_type_rejected(self):
        r = client.get(
            "/api/quality-guardian/first-pass-yield", params={"scope_type": "not_a_scope"}, headers=AUTH_OPERATOR,
        )
        assert r.status_code == 422

    def test_all_scopes_endpoint(self):
        r = client.get("/api/quality-guardian/first-pass-yield/all-scopes", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        body = r.json()
        for key in ("overall", "by_department", "by_instrument", "by_technician", "by_facility"):
            assert key in body


class TestDashboardAggregation:
    def test_command_center_returns_expected_shape(self):
        _create_event()
        r = client.get("/api/quality-guardian/command-center", headers=AUTH_MGR)
        assert r.status_code == 200
        body = r.json()
        for key in (
            "quality_events", "recurring_findings", "capas", "root_causes", "first_pass_yield",
            "technician_trends", "vendor_trends", "manufacturer_trends",
        ):
            assert key in body
        assert body["human_review_required"] is True

    def test_command_center_requires_leadership_role(self):
        r = client.get("/api/quality-guardian/command-center", headers=AUTH_VIEWER)
        assert r.status_code == 403

    def test_learning_loop_requires_confirmed_event(self):
        event = _create_event()
        r = client.post(f"/api/quality-guardian/events/{event['id']}/learning-loop", headers=AUTH_MGR)
        assert r.status_code == 422

    def test_learning_loop_updates_clinical_memory_for_confirmed_significant_event(self):
        case_id = _make_case()
        insp_id = _make_inspection(instrument_barcode="loop-001", risk_score=90)
        _link_inspection_to_case(insp_id, case_id)
        event = _create_event(case_id=case_id, severity="critical")
        client.post(f"/api/quality-guardian/events/{event['id']}/correlate", headers=AUTH_OPERATOR)
        client.post(f"/api/quality-guardian/events/{event['id']}/confirm", json={}, headers=AUTH_MGR)

        r = client.post(f"/api/quality-guardian/events/{event['id']}/learning-loop", headers=AUTH_MGR)
        assert r.status_code == 200
        assert r.json()["clinical_memory_updated"] is True
