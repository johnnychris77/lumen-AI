"""Phase 21 — SPD Clinical Knowledge Graph & Clinical Reasoning Engine tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.inspection import Inspection
from app.models.supervisor_review import SupervisorReview
from app.services.instrument_family_profiles import INSTRUMENT_FAMILY_PROFILES, get_family_profile
from app.services.knowledge_graph_service import reasoning_chain

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_MGR = {"Authorization": "Bearer manager-token"}
AUTH_VIEWER = {"Authorization": "Bearer viewer-token"}
SHA = "5eed0000" + "0" * 56


class TestGraphSchema:
    def test_schema_returns_nodes_and_relationships(self):
        res = client.get("/api/knowledge-graph/schema", headers=AUTH_ADMIN)
        assert res.status_code == 200
        data = res.json()
        assert "Instrument" in data["node_types"]
        assert "Manufacturer" in data["node_types"]
        assert "ClinicalRecommendation" in data["node_types"]
        assert "Supervisor VALIDATES Finding" in data["relationship_types"]
        assert data["chain"][0] == "Instrument"
        assert data["chain"][-1] == "Learning"

    def test_unauthenticated_rejected(self):
        res = client.get("/api/knowledge-graph/schema")
        assert res.status_code in (401, 403)


class TestInstrumentFamilyProfiles:
    def test_all_ten_families_defined(self):
        expected = {
            "rigid_scope", "flexible_endoscope", "kerrison", "needle_holder", "scissors",
            "drill_bit", "laparoscopic_instruments", "cannulated_instruments",
            "orthopedic_instruments", "micro_instruments",
        }
        assert expected == set(INSTRUMENT_FAMILY_PROFILES)

    def test_kerrison_profile_has_real_anatomy(self):
        profile = get_family_profile("kerrison")
        assert profile["display_name"] == "Kerrison"
        assert "jaw" in profile["typical_anatomy"]
        assert "serrations" in profile["typical_anatomy"]
        assert "box lock" in profile["high_risk_zones"]

    def test_profile_has_required_fields(self):
        profile = get_family_profile("scissors")
        for key in (
            "typical_contamination", "typical_damage", "typical_repair_issues",
            "inspection_priorities", "cleaning_priorities", "supervisor_focus_areas",
        ):
            assert key in profile

    def test_api_lists_all_families(self):
        res = client.get("/api/knowledge-graph/instrument-families", headers=AUTH_VIEWER)
        assert res.status_code == 200
        assert len(res.json()["families"]) == 10

    def test_api_unknown_family_404(self):
        res = client.get("/api/knowledge-graph/instrument-families/not-a-family", headers=AUTH_VIEWER)
        assert res.status_code == 404


class TestReasoningChain:
    def test_blood_in_scissors_hinge_chain(self):
        result = reasoning_chain("scissors", "blood", manufacturer="Acme Surgical")
        nodes = {s["node"]: s for s in result["chain"]}
        assert nodes["Instrument"]["value"] == "scissors"
        assert nodes["Manufacturer"]["value"] == "Acme Surgical"
        assert nodes["Instrument Family"]["value"] == "scissors"
        assert nodes["Inspection Zone"]["value"] == "hinge"
        assert nodes["Recommended Action"]["outcome"] == "REPROCESS"

    def test_narrative_names_finding_and_zone(self):
        result = reasoning_chain("scissors", "blood")
        narrative = result["narrative"].lower()
        assert "blood" in narrative
        assert "hinge" in narrative
        assert "supervisor" in narrative  # contamination narrative recommends supervisor verification

    def test_structural_finding_routes_to_remove_from_service(self):
        result = reasoning_chain("orthopedic drill", "crack")
        nodes = {s["node"]: s for s in result["chain"]}
        assert nodes["Recommended Action"]["outcome"] == "REMOVE FROM SERVICE"

    def test_api_reasoning_chain_endpoint(self):
        res = client.get(
            "/api/knowledge-graph/reasoning-chain",
            params={"instrument_type": "scissors", "finding_type": "blood"},
            headers=AUTH_VIEWER,
        )
        assert res.status_code == 200
        data = res.json()
        assert "chain" in data
        assert "narrative" in data
        assert data["human_review_required"] is True


class TestExplainabilityGraph:
    def test_why_expansion_for_real_inspection(self):
        db = SessionLocal()
        try:
            insp = Inspection(
                tenant_id="default-tenant", file_name="x.jpg", instrument_type="scissors",
                has_image=True, image_sha256=SHA, score_status="scored", risk_score=55,
                detected_issue="blood", recommended_action="Reprocess — blood. Return for complete cleaning.",
            )
            db.add(insp)
            db.commit()
            db.refresh(insp)
            insp_id = insp.id
        finally:
            db.close()

        res = client.get(f"/api/knowledge-graph/explain/{insp_id}", headers=AUTH_MGR)
        assert res.status_code == 200
        data = res.json()
        why_nodes = [w["node"] for w in data["why"]]
        # v2.5 (Project Cortex) extends the chain with Corrective Action and
        # Disposition — the two nodes the Clinical Reasoning Graph adds
        # beyond the original Phase 21 chain.
        assert why_nodes == [
            "Finding", "Zone", "Clinical Significance", "SPD Rule",
            "Corrective Action", "Recommendation", "Disposition",
        ]
        finding_node = next(w for w in data["why"] if w["node"] == "Finding")
        assert finding_node["value"] == "blood"
        zone_node = next(w for w in data["why"] if w["node"] == "Zone")
        assert zone_node["value"] == "hinge"

    def test_missing_inspection_404(self):
        res = client.get("/api/knowledge-graph/explain/99999999", headers=AUTH_MGR)
        assert res.status_code == 404


class TestKnowledgeGraphExplorer:
    def test_explore_zone_returns_cleaning_knowledge(self):
        res = client.get("/api/knowledge-graph/explore", params={"category": "zone", "q": "hinge"}, headers=AUTH_VIEWER)
        assert res.status_code == 200
        results = res.json()["results"]
        assert any(r["zone"] == "hinge" for r in results)
        hinge = next(r for r in results if r["zone"] == "hinge")
        assert "cleaning_method" in hinge["cleaning"]
        assert "brush_type" in hinge["cleaning"]

    def test_explore_finding_returns_clinical_education(self):
        res = client.get("/api/knowledge-graph/explore", params={"category": "finding", "q": "blood"}, headers=AUTH_VIEWER)
        results = res.json()["results"]
        assert any(r["finding"] == "blood" for r in results)

    def test_explore_recommendation_returns_five_outcomes(self):
        res = client.get("/api/knowledge-graph/explore", params={"category": "recommendation"}, headers=AUTH_VIEWER)
        results = res.json()["results"]
        outcomes = {r["outcome"] for r in results}
        assert outcomes == {"PASS", "MONITOR", "SUPERVISOR REVIEW", "REPROCESS", "REMOVE FROM SERVICE"}

    def test_explore_unknown_category(self):
        res = client.get("/api/knowledge-graph/explore", params={"category": "nonsense"}, headers=AUTH_VIEWER)
        assert res.status_code == 200
        assert res.json()["results"] == []


class TestEnterpriseKnowledgeAnalytics:
    def test_analytics_returns_required_keys(self):
        res = client.get("/api/knowledge-graph/analytics", headers=AUTH_ADMIN)
        assert res.status_code == 200
        data = res.json()
        for key in (
            "most_common_findings_by_manufacturer", "most_common_findings_by_anatomy",
            "highest_risk_anatomy_zone", "most_common_repair_reason",
            "most_common_supervisor_override", "most_difficult_instrument_family",
            "most_missed_anatomy_zones", "most_common_contamination_type",
        ):
            assert key in data

    def test_viewer_forbidden(self):
        res = client.get("/api/knowledge-graph/analytics", headers=AUTH_VIEWER)
        assert res.status_code == 403


class TestContinuousKnowledgeLearning:
    def test_learning_confidence_reflects_new_review(self):
        before = client.get("/api/knowledge-graph/learning-confidence", headers=AUTH_ADMIN).json()
        before_n = before["sample_sizes"]["supervisor_reviews"]

        db = SessionLocal()
        try:
            db.add(SupervisorReview(
                inspection_id=999999, tenant_id="default-tenant", reviewer_name="t",
                reviewer_role="spd_manager", agreement="agree", finding_correct=True, zone_correct=True,
            ))
            db.commit()
        finally:
            db.close()

        after = client.get("/api/knowledge-graph/learning-confidence", headers=AUTH_ADMIN).json()
        assert after["sample_sizes"]["supervisor_reviews"] == before_n + 1

    def test_learning_confidence_required_keys(self):
        data = client.get("/api/knowledge-graph/learning-confidence", headers=AUTH_ADMIN).json()
        for key in (
            "knowledge_confidence", "reasoning_confidence", "clinical_recommendation_confidence",
            "zone_confidence", "instrument_profile_confidence_by_family", "sample_sizes",
        ):
            assert key in data
