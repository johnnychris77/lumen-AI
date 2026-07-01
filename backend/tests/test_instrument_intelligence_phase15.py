"""Phase 15 — Instrument Intelligence Engine: anatomy, coverage, risk map,
missing-image guidance, knowledge library, analytics."""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import analyze_inspection
from app.services.instrument_anatomy import get_anatomy, resolve_family
from app.services.inspection_coverage import (
    compute_coverage, missing_image_guidance, build_risk_map,
)

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}
SHA = "a1b2c3d4" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"p15-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _analyze(itype, declared=None, inspected_zones=None):
    _baseline(itype)
    db = SessionLocal()
    try:
        return analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant",
            has_image=True, image_sha256=SHA, declared_findings=declared,
            inspected_zones=inspected_zones,
        )
    finally:
        db.close()


class TestAnatomyLibrary:
    def test_rigid_scope_includes_oring(self):
        a = get_anatomy("rigid scope")
        assert "o-ring area" in a["zone_names"]
        assert "working channel" in a["zone_names"]

    def test_drill_bit_includes_flutes_and_threads(self):
        a = get_anatomy("orthopedic drill")
        assert "flutes" in a["zone_names"]
        assert "threaded region" in a["zone_names"]

    def test_kerrison_includes_serration_box_lock_hinge(self):
        a = get_anatomy("kerrison rongeur")
        for z in ("serrations", "box lock", "hinge"):
            assert z in a["zone_names"]

    def test_laparoscopic_includes_insulation_and_lumen(self):
        a = get_anatomy("laparoscopic grasper")
        assert "insulation edge" in a["zone_names"]
        assert any("lumen" in z for z in a["zone_names"])

    def test_default_family_for_unknown(self):
        assert resolve_family("mystery tool") == "default"


class TestCoverageEngine:
    def test_complete_coverage(self):
        req = get_anatomy("kerrison")["required_images"]
        cov = compute_coverage("kerrison", req)
        assert cov["overall_coverage"] == 100
        assert cov["missing"] == []
        assert cov["quality"] == "complete"

    def test_missing_zone_lowers_coverage(self):
        req = get_anatomy("kerrison")["required_images"]
        cov = compute_coverage("kerrison", req[:-2])  # drop two required
        assert cov["overall_coverage"] < 100
        assert cov["missing"]
        assert cov["message"] and "incomplete" in cov["message"].lower()

    def test_missing_image_guidance(self):
        g = missing_image_guidance("rigid scope", ["distal tip"])
        assert any("o-ring area" in item for item in g)

    def test_risk_map_rows(self):
        rmap = build_risk_map("kerrison", {"serrations": ["blood"]}, ["serrations"])
        row = next(r for r in rmap if r["zone"] == "serrations")
        assert row["inspected"] is True
        assert row["findings"] == ["blood"]
        assert row["recommended_manual_check"]


class TestAnalyzeIntegration:
    def test_analysis_carries_anatomy_and_coverage(self):
        out = _analyze("kerrison", inspected_zones=["serrations", "box lock"])
        assert "instrument_anatomy" in out
        assert "inspection_coverage" in out
        assert "risk_map" in out
        assert "missing_image_guidance" in out
        assert out["inspection_coverage"]["overall_coverage"] <= 100

    def test_findings_have_recommended_action(self):
        out = _analyze("serrated forceps")
        for f in out["predicted_findings"]:
            assert f["recommended_action"] in (
                "Clear", "Monitor", "Supervisor review", "Reprocess", "Remove from service"
            )

    def test_mentor_has_zone_reasoning(self):
        out = _analyze("orthopedic drill", declared=["debris"])
        mentor = out["clinical_decision"]["ai_mentor"]
        assert "where_was_it_detected" in mentor
        assert "why_this_zone_is_high_risk" in mentor


class TestKnowledgeAndAnalytics:
    def test_register_and_list_knowledge(self):
        r = client.post("/api/instrument-knowledge", json={
            "manufacturer": "Acme", "model": "RS-100", "instrument_family": "rigid_scope",
            "ifu_reference": "IFU-RS-100", "anatomy_zones": ["distal tip", "o-ring area"],
            "high_risk_zones": ["o-ring area"], "known_failure_modes": ["seal wear"],
            "maintenance_interval": "annual", "repair_criteria": "seal leak",
            "replacement_criteria": "cracked sheath",
        }, headers=AUTH_ADMIN)
        assert r.status_code == 201, r.text
        lst = client.get("/api/instrument-knowledge", headers=AUTH_ADMIN).json()
        assert any(e["manufacturer"] == "Acme" for e in lst["entries"])

    def test_operator_cannot_register_knowledge(self):
        r = client.post("/api/instrument-knowledge", json={"manufacturer": "X"}, headers=AUTH_OPERATOR)
        assert r.status_code == 403

    def test_anatomy_endpoint(self):
        r = client.get("/api/instrument-anatomy/rigid%20scope", headers=AUTH_OPERATOR)
        assert r.status_code == 200
        assert "o-ring area" in r.json()["zone_names"]

    def test_zone_analytics_no_fabrication(self):
        r = client.get("/api/analytics/zone-intelligence", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["contamination_rate_by_zone"] == {}  # not fabricated
        assert "supervisor_override_by_zone" in body
