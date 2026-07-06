"""Phase 23 — Clinical Intelligence Operating System (CIOS) tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.cios.context import ClinicalContext
from app.cios.governance import governance_snapshot
from app.cios.orchestrator import run_cios_pipeline
from app.cios.rule_registry import CLINICAL_RULE_REGISTRY, get_rule
from app.cios.state_machine import INSPECTION_STATES, derive_state, is_valid_transition
from app.db.session import SessionLocal
from app.models.inspection import Inspection

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
SHA = "c105c105" + "0" * 56


def _make_inspection(db, **overrides) -> Inspection:
    defaults = dict(
        tenant_id="default-tenant", file_name="x.jpg", instrument_type="kerrison rongeur",
        has_image=True, image_sha256=SHA, score_status="scored", risk_score=60,
        detected_issue="blood", vendor_name="Acme Surgical",
        recommended_action="Reprocess — blood. Return for complete cleaning.",
        supervisor_review_required=False, inspected_zones_json="null",
    )
    defaults.update(overrides)
    insp = Inspection(**defaults)
    db.add(insp)
    db.commit()
    db.refresh(insp)
    return insp


class TestClinicalContextImmutable:
    def test_context_is_frozen(self):
        ctx = ClinicalContext(inspection_id=1, tenant_id="default-tenant", instrument_type="scissors")
        try:
            ctx.instrument_type = "forceps"
            assert False, "expected a validation error on mutating a frozen model"
        except Exception:
            pass

    def test_with_updates_returns_new_instance(self):
        ctx = ClinicalContext(inspection_id=1, tenant_id="default-tenant", instrument_type="scissors")
        updated = ctx.with_updates(instrument_type="forceps")
        assert ctx.instrument_type == "scissors"
        assert updated.instrument_type == "forceps"
        assert ctx is not updated


class TestInspectionStateMachine:
    def test_new_inspection_no_image(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, has_image=False, score_status="pending", detected_issue="none")
        finally:
            db.close()
        state = derive_state(insp)
        assert state["current_state"] == "NEW"

    def test_scored_no_review_is_analyzed(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
        finally:
            db.close()
        state = derive_state(insp, review=None)
        assert state["current_state"] == "ANALYZED"
        assert "ANALYZED" in state["states_reached"]

    def test_valid_transitions(self):
        assert is_valid_transition("NEW", "IMAGE_CAPTURED") is True
        assert is_valid_transition("NEW", "COMPLETE") is False
        assert is_valid_transition("SUPERVISOR_PENDING", "APPROVED") is True
        assert is_valid_transition("SUPERVISOR_PENDING", "REQUIRES_ACTION") is True
        assert is_valid_transition("COMPLETE", "NEW") is False

    def test_all_states_are_reachable_in_order(self):
        assert INSPECTION_STATES[0] == "NEW"
        assert INSPECTION_STATES[-1] == "COMPLETE"


class TestPipelineExecutionAndMonitor:
    def test_run_cios_pipeline_returns_all_sections(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
        finally:
            db.close()

        db = SessionLocal()
        try:
            row = db.query(Inspection).filter(Inspection.id == insp.id).first()
            result = run_cios_pipeline(db, row, "default-tenant")
        finally:
            db.close()

        for key in (
            "clinical_context", "pipeline_monitor", "inspection_state", "timeline",
            "events_emitted", "decision_ledger_entry_id", "governance", "agent_result",
        ):
            assert key in result

    def test_pipeline_monitor_shows_supervisor_pending_before_review(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            insp_id = insp.id
        finally:
            db.close()

        res = client.get(f"/api/cios/run/{insp_id}", headers=AUTH_ADMIN)
        assert res.status_code == 200
        monitor = {m["agent"]: m["status"] for m in res.json()["pipeline_monitor"]}
        assert monitor["Supervisor Agent"] == "Pending"
        assert monitor["Learning Agent"] == "Queued"
        assert monitor["Enterprise Agent"] == "Queued"
        assert monitor["Instrument Agent"] == "Complete"
        assert monitor["Recommendation Agent"] == "Complete"

    def test_pipeline_monitor_shows_supervisor_complete_after_review(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, instrument_type="scissors")
            insp_id = insp.id
        finally:
            db.close()

        client.post(
            f"/api/inspections/{insp_id}/supervisor-review",
            json={"agreement": "agree", "finding_correct": True},
            headers=AUTH_MGR,
        )

        res = client.get(f"/api/cios/run/{insp_id}", headers=AUTH_ADMIN)
        monitor = {m["agent"]: m["status"] for m in res.json()["pipeline_monitor"]}
        assert monitor["Supervisor Agent"] == "Complete"
        assert monitor["Learning Agent"] == "Complete"


class TestEventGeneration:
    def test_blood_detection_emits_event(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, detected_issue="blood")
            insp_id = insp.id
        finally:
            db.close()

        res = client.get(f"/api/cios/run/{insp_id}", headers=AUTH_ADMIN)
        event_types = {e["event_type"] for e in res.json()["events_emitted"]}
        assert "InspectionStarted" in event_types
        assert "BloodDetected" in event_types
        assert "RecommendationGenerated" in event_types

    def test_events_endpoint_filters_by_inspection(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            insp_id = insp.id
        finally:
            db.close()

        client.get(f"/api/cios/run/{insp_id}", headers=AUTH_ADMIN)
        res = client.get("/api/cios/events", params={"inspection_id": insp_id}, headers=AUTH_ADMIN)
        assert res.status_code == 200
        events = res.json()["events"]
        assert len(events) > 0
        assert all(e["inspection_id"] == insp_id for e in events)


class TestDecisionLedger:
    def test_ai_recommendation_recorded(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            insp_id = insp.id
        finally:
            db.close()

        client.get(f"/api/cios/run/{insp_id}", headers=AUTH_ADMIN)
        res = client.get(f"/api/cios/decision-ledger/{insp_id}", headers=AUTH_ADMIN)
        assert res.status_code == 200
        decisions = res.json()["decisions"]
        assert any(d["decision_type"] == "ai_recommendation" and d["made_by"] == "ai" for d in decisions)
        for d in decisions:
            assert d["model_version"]
            assert d["ontology_version"]

    def test_supervisor_decision_recorded_via_review_endpoint(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, instrument_type="forceps")
            insp_id = insp.id
        finally:
            db.close()

        client.post(
            f"/api/inspections/{insp_id}/supervisor-review",
            json={"agreement": "agree", "finding_correct": True},
            headers=AUTH_MGR,
        )
        res = client.get(f"/api/cios/decision-ledger/{insp_id}", headers=AUTH_ADMIN)
        decisions = res.json()["decisions"]
        assert any(d["decision_type"] == "supervisor_approval" for d in decisions)


class TestTimelineCreation:
    def test_timeline_has_inspection_created_and_agent_entries(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            insp_id = insp.id
        finally:
            db.close()

        res = client.get(f"/api/cios/run/{insp_id}", headers=AUTH_ADMIN)
        timeline = res.json()["timeline"]
        assert "Inspection created" in timeline[0]["label"]
        assert any("Recommendation Agent" in e["label"] for e in timeline)
        assert all(e["timestamp"] for e in timeline)


class TestGovernanceVersions:
    def test_governance_endpoint_returns_all_versions(self):
        res = client.get("/api/cios/governance", headers=AUTH_ADMIN)
        assert res.status_code == 200
        data = res.json()
        for key in (
            "architecture_version", "ontology_version", "knowledge_graph_version",
            "model_version", "dataset_version", "clinical_rule_version", "inspection_pipeline_version",
        ):
            assert data[key]
        assert data == governance_snapshot()


class TestClinicalRuleRegistry:
    def test_registry_has_rules_with_required_fields(self):
        assert len(CLINICAL_RULE_REGISTRY) >= 5
        for rule in CLINICAL_RULE_REGISTRY:
            for key in ("rule_id", "name", "purpose", "evidence", "applies_to", "priority", "version", "approval_status"):
                assert key in rule

    def test_get_rule_by_id(self):
        rule = get_rule("RULE-001")
        assert rule is not None
        assert rule["name"] == "Structural defect escalation"

    def test_rule_registry_endpoint(self):
        res = client.get("/api/cios/rule-registry", headers=AUTH_ADMIN)
        assert res.status_code == 200
        assert len(res.json()["rules"]) >= 5


class TestCertificateGeneration:
    def test_certificate_json_not_a_sterilization_certificate(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            insp_id = insp.id
        finally:
            db.close()

        res = client.get(f"/api/cios/certificate/{insp_id}", headers=AUTH_ADMIN)
        assert res.status_code == 200
        data = res.json()
        assert data["not_a_sterilization_certificate"] is True
        assert data["inspection_id"] == insp_id
        assert "digital_signature_placeholder" in data
        assert data["digital_signature_placeholder"]["signed"] is False

    def test_certificate_pdf_downloads(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            insp_id = insp.id
        finally:
            db.close()

        res = client.get(f"/api/cios/certificate/{insp_id}/pdf", headers=AUTH_ADMIN)
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content[:4] == b"%PDF"


class TestCiosDashboard:
    def test_dashboard_returns_required_keys(self):
        res = client.get("/api/cios/dashboard", headers=AUTH_ADMIN)
        assert res.status_code == 200
        data = res.json()
        for key in (
            "system_health", "inspection_throughput", "coverage_rate",
            "supervisor_agreement_rate", "ai_confidence", "governance_versions",
            "digital_twin_health", "most_common_findings", "most_common_zones",
            "enterprise_risk_index",
        ):
            assert key in data

    def test_unauthenticated_rejected(self):
        res = client.get("/api/cios/dashboard")
        assert res.status_code in (401, 403)
