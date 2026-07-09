"""v2.5 — Project Sentinel: Predictive Simulation & Clinical Scenario Engine tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.inspection import Inspection
from app.models.simulation_engine import (
    RECLEAN,
    REMOVE_FROM_SERVICE,
    REPAIR_EVALUATION,
    SCENARIO_KEYS,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA = "5e17ine1" + "0" * 56
TENANT = "default-tenant"


def _make_inspection(
    *, instrument_type="kerrison_rongeur", detected_issue="corrosion", risk_score=80,
    recommended_action="Remove from service — corrosion detected.", coverage_pct=90,
    tenant_id=TENANT, barcode=None,
) -> int:
    db = SessionLocal()
    try:
        insp = Inspection(
            tenant_id=tenant_id, file_name="x.jpg", instrument_type=instrument_type,
            has_image=True, image_sha256=SHA, score_status="scored", risk_score=risk_score,
            detected_issue=detected_issue, recommended_action=recommended_action,
            coverage_pct=coverage_pct, instrument_barcode=barcode,
        )
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


class TestScenarioGeneration:
    def test_generate_returns_four_scenarios(self):
        insp_id = _make_inspection()
        r = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR)
        assert r.status_code == 200, r.text
        body = r.json()
        assert {s["scenario_key"] for s in body["scenarios"]} == set(SCENARIO_KEYS)
        assert len(body["alternatives"]) == 3

    def test_generate_unauthenticated_rejected(self):
        insp_id = _make_inspection()
        r = client.post(f"/api/scenario-analysis/{insp_id}/generate")
        assert r.status_code in (401, 403)

    def test_generate_missing_inspection_404(self):
        r = client.post("/api/scenario-analysis/999999999/generate", headers=AUTH_OPERATOR)
        assert r.status_code == 404

    def test_generate_has_disclaimer_and_human_review(self):
        insp_id = _make_inspection()
        body = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR).json()
        assert body["human_review_required"] is True
        assert len(body["disclaimer"]) > 10

    def test_remove_from_service_finding_recommends_remove_from_service(self):
        insp_id = _make_inspection(
            detected_issue="missing_component", recommended_action="Remove from service — missing component detected.",
        )
        body = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR).json()
        assert body["recommended_scenario"] == REMOVE_FROM_SERVICE
        assert body["recommended"]["scenario_key"] == REMOVE_FROM_SERVICE

    def test_contamination_finding_recommends_reclean(self):
        insp_id = _make_inspection(
            detected_issue="blood", risk_score=40, recommended_action="Reprocess — blood detected.",
        )
        body = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR).json()
        assert body["recommended_scenario"] == RECLEAN

    def test_tenant_isolation_cannot_see_other_tenant_inspection(self):
        insp_id = _make_inspection(tenant_id="other-tenant")
        r = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR)
        assert r.status_code == 404


class TestRecommendationComparison:
    def test_exactly_one_scenario_is_recommended(self):
        insp_id = _make_inspection()
        body = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR).json()
        recommended_flags = [s["is_recommended"] for s in body["scenarios"]]
        assert sum(recommended_flags) == 1

    def test_each_scenario_has_risk_projection_fields(self):
        insp_id = _make_inspection()
        body = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR).json()
        for s in body["scenarios"]:
            for field in (
                "quality_risk", "operational_impact", "repeat_inspection_probability",
                "repair_likelihood", "supervisor_workload_impact", "confidence_level",
            ):
                assert field in s
                assert 0.0 <= s[field] <= 1.0

    def test_evidence_and_reasoning_present(self):
        insp_id = _make_inspection()
        body = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR).json()
        assert isinstance(body["evidence"], list)
        assert len(body["evidence"]) > 0
        assert len(body["reasoning"]) > 5


class TestGetScenarioAnalysis:
    def test_get_before_generate_returns_404(self):
        insp_id = _make_inspection()
        r = client.get(f"/api/scenario-analysis/{insp_id}", headers=AUTH_OPERATOR)
        assert r.status_code == 404

    def test_get_after_generate_returns_latest_run(self):
        insp_id = _make_inspection()
        client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR)
        r = client.get(f"/api/scenario-analysis/{insp_id}", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert r.json()["inspection_id"] == insp_id


class TestWorkflowImpact:
    def test_workflow_impact_requires_existing_run(self):
        insp_id = _make_inspection()
        r = client.get(f"/api/scenario-analysis/{insp_id}/workflow-impact", headers=AUTH_OPERATOR)
        assert r.status_code == 404

    def test_workflow_impact_calculation(self):
        insp_id = _make_inspection()
        client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR)
        r = client.get(f"/api/scenario-analysis/{insp_id}/workflow-impact", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        body = r.json()
        for field in (
            "inspection_queue_impact_hours", "or_readiness_impact", "repair_backlog_impact",
            "technician_workload_impact", "supervisor_workload_impact", "instrument_availability_impact",
        ):
            assert field in body
        assert body["or_readiness_impact"] in ("none", "minor_delay", "significant_delay")


class TestInstrumentHealthProjection:
    def test_no_history_returns_404(self):
        r = client.get(
            "/api/scenario-analysis/instrument-health", params={"instrument_barcode": "no-such-barcode"},
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 404

    def test_missing_identity_param_422(self):
        r = client.get("/api/scenario-analysis/instrument-health", headers=AUTH_OPERATOR)
        assert r.status_code == 422

    def test_projects_health_trend_for_tracked_instrument(self):
        barcode = "sim-eng-barcode-001"
        _make_inspection(barcode=barcode, detected_issue="corrosion", recommended_action="Remove from service — corrosion detected.")
        _make_inspection(barcode=barcode, detected_issue="corrosion", recommended_action="Remove from service — corrosion detected.")
        r = client.get(
            "/api/scenario-analysis/instrument-health", params={"instrument_barcode": barcode},
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["health_trend"] in ("improving", "stable", "declining", "insufficient_data")
        assert body["human_review_required"] is True


class TestEducationalScenarioMode:
    def test_compare_returns_three_scenarios(self):
        r = client.get(
            "/api/scenario-analysis/education/compare",
            params={"instrument_type": "kerrison_rongeur", "finding_type": "corrosion"},
            headers=AUTH_OPERATOR,
        )
        assert r.status_code == 200
        body = r.json()
        keys = {c["scenario_key"] for c in body["comparisons"]}
        assert keys == {RECLEAN, REPAIR_EVALUATION, REMOVE_FROM_SERVICE}


class TestOutcomeLearning:
    def test_record_actual_outcome_matches_prediction(self):
        insp_id = _make_inspection(
            detected_issue="missing_component", recommended_action="Remove from service — missing component detected.",
        )
        run = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR).json()
        r = client.post(
            f"/api/scenario-analysis/{run['id']}/actual-outcome",
            json={"actual_disposition": "Remove From Service", "notes": "Confirmed by supervisor"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["prediction_correct"] is True
        assert body["actual_disposition"] == "Remove From Service"

    def test_record_actual_outcome_mismatched_prediction(self):
        insp_id = _make_inspection(
            detected_issue="missing_component", recommended_action="Remove from service — missing component detected.",
        )
        run = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR).json()
        r = client.post(
            f"/api/scenario-analysis/{run['id']}/actual-outcome",
            json={"actual_disposition": "Reclean"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 200
        assert r.json()["prediction_correct"] is False

    def test_actual_outcome_requires_leadership_role(self):
        insp_id = _make_inspection()
        run = client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR).json()
        r = client.post(
            f"/api/scenario-analysis/{run['id']}/actual-outcome",
            json={"actual_disposition": "reclean"},
            headers=AUTH_VIEWER,
        )
        assert r.status_code == 403

    def test_actual_outcome_missing_run_404(self):
        r = client.post(
            "/api/scenario-analysis/999999999/actual-outcome",
            json={"actual_disposition": "reclean"},
            headers=AUTH_MGR,
        )
        assert r.status_code == 404


class TestEnterpriseScenarioAnalytics:
    def test_analytics_returns_expected_shape(self):
        insp_id = _make_inspection()
        client.post(f"/api/scenario-analysis/{insp_id}/generate", headers=AUTH_OPERATOR)
        r = client.get("/api/scenario-analysis/analytics", headers=AUTH_MGR)
        assert r.status_code == 200
        body = r.json()
        assert set(body["most_common_scenarios"]) == set(SCENARIO_KEYS)
        assert "prediction_accuracy" in body
        assert "override_outcomes" in body

    def test_analytics_requires_leadership_role(self):
        r = client.get("/api/scenario-analysis/analytics", headers=AUTH_VIEWER)
        assert r.status_code == 403
