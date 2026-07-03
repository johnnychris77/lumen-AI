"""Phase 22 — Multi-Agent Clinical Intelligence Platform tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.agents.anatomy_agent import AnatomyIntelligenceAgent
from app.agents.context import InstrumentContext
from app.agents.contamination_agent import ContaminationDetectionAgent
from app.agents.damage_agent import DamageDetectionAgent
from app.agents.instrument_agent import InstrumentIntelligenceAgent
from app.agents.orchestrator import run_pipeline
from app.agents.registry import PIPELINE_ORDER, get_registry
from app.db.session import SessionLocal
from app.models.inspection import Inspection

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA = "a9e17700" + "0" * 56


def _make_inspection(db, **overrides) -> Inspection:
    defaults = dict(
        tenant_id="default-tenant", file_name="x.jpg", instrument_type="kerrison rongeur",
        has_image=True, image_sha256=SHA, score_status="scored", risk_score=60,
        detected_issue="blood", vendor_name="Acme Surgical",
        recommended_action="Reprocess — blood. Return for complete cleaning.",
        inspected_zones_json="null",
    )
    defaults.update(overrides)
    insp = Inspection(**defaults)
    db.add(insp)
    db.commit()
    db.refresh(insp)
    return insp


class TestAgentContextValidation:
    def test_instrument_context_requires_family(self):
        ctx = InstrumentContext(instrument_type="scissors", instrument_family="scissors", instrument_category="cutting")
        assert ctx.instrument_type == "scissors"
        assert ctx.digital_twin_available is False

    def test_anatomy_agent_consumes_instrument_context(self):
        instrument_agent = InstrumentIntelligenceAgent()
        db = SessionLocal()
        try:
            instrument_ctx = instrument_agent.run(db, "default-tenant", "kerrison rongeur")
        finally:
            db.close()
        anatomy_ctx = AnatomyIntelligenceAgent().run(instrument_ctx, None)
        assert anatomy_ctx.instrument_family == instrument_ctx.instrument_family
        assert anatomy_ctx.inspected_zones is None
        assert anatomy_ctx.inspection_completeness is None


class TestAgentCommunication:
    """Agents only communicate through typed context objects — never raw dicts."""

    def test_contamination_agent_owns_only_contamination_types(self):
        ctx = ContaminationDetectionAgent().run("scissors", "crack", 50.0, 80)
        assert ctx.has_contamination is False
        assert ctx.findings == []

    def test_damage_agent_owns_only_damage_types(self):
        ctx = DamageDetectionAgent().run("blood", 60)
        assert ctx.has_damage is False

    def test_contamination_agent_produces_zone_and_significance(self):
        ctx = ContaminationDetectionAgent().run("scissors", "blood", 80.0, 60)
        assert ctx.has_contamination is True
        assert ctx.findings[0].zone == "hinge"
        assert ctx.findings[0].clinical_significance

    def test_damage_agent_flags_repairable_issue(self):
        ctx = DamageDetectionAgent().run("crack", 75)
        assert ctx.has_damage is True
        assert "repair" in ctx.findings[0].repair_recommendation.lower()


class TestAgentRegistry:
    def test_registry_lists_all_ten_agents(self):
        registry = get_registry()
        assert len(registry) == 10
        assert len(PIPELINE_ORDER) == 10

    def test_registry_entries_have_required_fields(self):
        for entry in get_registry():
            for key in ("name", "version", "capabilities", "depends_on", "pipeline_position", "status", "health"):
                assert key in entry
            assert entry["health"] == "ok"

    def test_registry_api_endpoint(self):
        res = client.get("/api/agents/registry", headers=AUTH_VIEWER)
        assert res.status_code == 200
        assert len(res.json()["agents"]) == 10

    def test_health_endpoint(self):
        res = client.get("/api/agents/health", headers=AUTH_VIEWER)
        assert res.status_code == 200
        assert res.json()["overall_status"] == "ok"

    def test_unauthenticated_rejected(self):
        res = client.get("/api/agents/registry")
        assert res.status_code in (401, 403)


class TestPipelineExecution:
    def test_orchestrator_runs_all_agents_for_real_inspection(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
        finally:
            db.close()

        db = SessionLocal()
        try:
            row = db.query(Inspection).filter(Inspection.id == insp.id).first()
            result = run_pipeline(db, row, "default-tenant")
        finally:
            db.close()

        for key in (
            "instrument_context", "anatomy_context", "coverage_context", "contamination_context",
            "damage_context", "clinical_reasoning_context", "recommendation_context",
            "supervisor_context", "learning_context", "enterprise_context", "trace",
        ):
            assert key in result

        assert result["recommendation_context"]["readiness_state"] == "REQUIRES_RECLEANING"
        assert result["contamination_context"]["has_contamination"] is True

    def test_api_run_endpoint(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db, detected_issue="crack", recommended_action="Remove from service — crack.")
            insp_id = insp.id
        finally:
            db.close()

        res = client.get(f"/api/agents/run/{insp_id}", headers=AUTH_ADMIN)
        assert res.status_code == 200
        data = res.json()
        assert data["recommendation_context"]["readiness_state"] == "REQUIRES_REPAIR"
        assert data["damage_context"]["has_damage"] is True

    def test_missing_inspection_404(self):
        res = client.get("/api/agents/run/999999999", headers=AUTH_ADMIN)
        assert res.status_code == 404


class TestReasoningTrace:
    def test_trace_has_ten_entries_in_pipeline_order(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            insp_id = insp.id
        finally:
            db.close()

        res = client.get(f"/api/agents/trace/{insp_id}", headers=AUTH_ADMIN)
        assert res.status_code == 200
        trace = res.json()["trace"]
        assert len(trace) == 10
        agent_names = [t["agent"] for t in trace]
        assert agent_names == [a.NAME for a in PIPELINE_ORDER]

    def test_trace_entry_shows_input_and_output(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            insp_id = insp.id
        finally:
            db.close()

        res = client.get(f"/api/agents/trace/{insp_id}", headers=AUTH_ADMIN)
        trace = res.json()["trace"]
        instrument_entry = trace[0]
        assert instrument_entry["agent"] == "Instrument Intelligence Agent"
        assert "input_summary" in instrument_entry
        assert "output_summary" in instrument_entry
        assert instrument_entry["output_summary"]["instrument_family"] == "kerrison_rongeur"

    def test_trace_final_recommendation_matches_run(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            insp_id = insp.id
        finally:
            db.close()

        run_result = client.get(f"/api/agents/run/{insp_id}", headers=AUTH_ADMIN).json()
        trace_result = client.get(f"/api/agents/trace/{insp_id}", headers=AUTH_ADMIN).json()
        assert trace_result["final_recommendation"] == run_result["recommendation_context"]


class TestSupervisorAgentNeverFabricates:
    def test_no_review_means_review_exists_false(self):
        db = SessionLocal()
        try:
            insp = _make_inspection(db)
            insp_id = insp.id
        finally:
            db.close()

        res = client.get(f"/api/agents/run/{insp_id}", headers=AUTH_ADMIN)
        data = res.json()
        assert data["supervisor_context"]["review_exists"] is False
        assert data["supervisor_context"]["agreement"] is None
