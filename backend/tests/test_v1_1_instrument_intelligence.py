"""LumenAI Inspect v1.1 — Instrument Intelligence & Anatomy Recognition.

Covers the v1.1-specific additions on top of the existing (Phase 15/22)
instrument-anatomy/coverage infrastructure:
  - GET /api/instrument-anatomy (list all anatomy families)
  - GET /api/instrument-zones (zone taxonomy reference)
  - GET /api/coverage-dashboard/summary (real aggregate coverage stats)
  - Supervisor correction of image view + missing zone (new SupervisorReview
    fields, on top of the existing instrument-family/zone correction fields)

Plus the full v1.1 scenario checklist against the anatomy/coverage services,
exercised through the public API contract.
"""
import json

from fastapi.testclient import TestClient

from app.main import app
from app.db import models
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.models.supervisor_review import SupervisorReview
from app.services.inspection_coverage import compute_coverage
from app.services.instrument_anatomy import get_anatomy

client = TestClient(app)
AUTH_ADMIN = {"Authorization": "Bearer dev-token"}
SHA = "beadfeed" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"v11-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _make_inspection(itype: str, inspected_zones=None) -> int:
    db = SessionLocal()
    try:
        insp = models.Inspection(
            tenant_id="default-tenant", file_name="f.jpg", instrument_type=itype,
            risk_score=20, score_status="scored", has_image=True, image_sha256=SHA,
            recommended_action="MONITOR",
            inspected_zones_json=json.dumps(inspected_zones),
        )
        db.add(insp)
        db.commit()
        db.refresh(insp)
        return insp.id
    finally:
        db.close()


# ── 1-5: instrument family / anatomy profile resolution via the public API ──

class TestInstrumentAnatomyProfiles:
    def test_rigid_scope_returns_oring_profile(self):
        r = client.get("/api/instrument-anatomy/rigid%20scope", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["instrument_family"] == "rigid_scope"
        assert "o-ring area" in body["anatomy_zones"]

    def test_flexible_endoscope_differs_from_rigid_scope(self):
        flex = client.get("/api/instrument-anatomy/flexible%20colonoscope", headers=AUTH_ADMIN).json()
        rigid = client.get("/api/instrument-anatomy/rigid%20scope", headers=AUTH_ADMIN).json()
        assert flex["instrument_family"] == "flexible_endoscope"
        assert rigid["instrument_family"] == "rigid_scope"
        assert "biopsy channel" in flex["anatomy_zones"]
        assert "biopsy channel" not in rigid["anatomy_zones"]
        assert "o-ring area" not in flex["anatomy_zones"]

    def test_drill_bit_returns_flute_threaded_profile(self):
        body = client.get("/api/instrument-anatomy/drill%20bit", headers=AUTH_ADMIN).json()
        assert body["instrument_family"] == "drill_bit"
        assert "flutes" in body["anatomy_zones"]
        assert "threaded region" in body["anatomy_zones"]

    def test_kerrison_returns_jaw_serration_boxlock_profile(self):
        body = client.get("/api/instrument-anatomy/kerrison%20rongeur", headers=AUTH_ADMIN).json()
        assert body["instrument_family"] == "kerrison_rongeur"
        for zone in ("jaw", "serrations", "box lock"):
            assert zone in body["anatomy_zones"]

    def test_unknown_instrument_returns_generic_spd_profile(self):
        body = client.get("/api/instrument-anatomy/mystery-widget-9000", headers=AUTH_ADMIN).json()
        assert body["instrument_family"] == "unknown"
        assert body["profile_found"] is False
        assert body["warning"] and "supervisor review" in body["warning"].lower()
        assert body["anatomy_zones"]  # generic zones still provided, nothing blank


# ── 6-7: Coverage Engine score behavior ──────────────────────────────────────

class TestCoverageScoreBehavior:
    def test_missing_high_risk_zone_lowers_coverage_score(self):
        # Kerrison's box lock and serrations are high-risk; tag only "jaw".
        cov = compute_coverage("kerrison rongeur", ["jaw"])
        assert cov["assessed"] is True
        assert "box lock" in cov["missing"] or "serrations" in cov["missing"]
        assert cov["overall_coverage"] < 100
        assert cov["quality"] in ("incomplete", "insufficient", "acceptable")

    def test_complete_required_zones_improves_coverage_score(self):
        anatomy = get_anatomy("kerrison rongeur")
        cov = compute_coverage("kerrison rongeur", anatomy["required_images"])
        assert cov["overall_coverage"] == 100
        assert cov["missing"] == []
        assert cov["quality"] in ("complete", "acceptable")


# ── 8: AI context includes the anatomy profile ───────────────────────────────

class TestAIContextAnatomyAware:
    def test_ai_analysis_includes_anatomy_profile_and_coverage(self):
        _baseline("kerrison rongeur")
        from app.services.baseline_comparison_scoring_service import analyze_inspection
        db = SessionLocal()
        try:
            result = analyze_inspection(
                db, instrument_type="kerrison rongeur", tenant_id="default-tenant",
                has_image=True, image_sha256=SHA, inspected_zones=["jaw", "box lock"],
            )
        finally:
            db.close()
        assert result["instrument_anatomy"]["family"] == "kerrison_rongeur"
        assert result["inspection_coverage"]["assessed"] is True
        assert "missing_image_guidance" in result
        assert "risk_map" in result and result["risk_map"]


# ── New v1.1 endpoints ────────────────────────────────────────────────────────

class TestAnatomyLibraryListEndpoint:
    def test_list_endpoint_returns_all_families(self):
        r = client.get("/api/instrument-anatomy", headers=AUTH_ADMIN)
        assert r.status_code == 200
        families = {f["family"] for f in r.json()["families"]}
        assert {"rigid_scope", "flexible_endoscope", "drill_bit", "kerrison_rongeur",
                "scissors", "needle_holder", "laparoscopic", "general_forceps"} <= families
        assert "default" not in families  # generic fallback excluded from the browse list


class TestZoneTaxonomyEndpoint:
    def test_zone_taxonomy_endpoint(self):
        r = client.get("/api/instrument-zones", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert "box lock" in body["high_retention_zones"]
        assert "serrations" in body["zone_info"]
        assert body["zone_info"]["serrations"]["risk"] == "high"


class TestCoverageDashboardEndpoint:
    def test_coverage_dashboard_summary_reflects_real_inspections(self):
        anatomy = get_anatomy("kerrison rongeur")
        _make_inspection("kerrison rongeur", anatomy["required_images"])
        _make_inspection("kerrison rongeur", ["jaw"])
        _make_inspection("kerrison rongeur", None)  # never tagged — excluded from average

        r = client.get("/api/coverage-dashboard/summary", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["assessed_count"] >= 2
        assert body["average_coverage"] is not None
        assert sum(body["coverage_status_breakdown"].values()) == body["assessed_count"]
        assert "kerrison_rongeur" in body["average_coverage_by_family"]


# ── 9: Supervisor can correct anatomy zone / image view / missing zone ──────

class TestSupervisorImageViewAndMissingZoneFeedback:
    def test_supervisor_can_correct_image_view_and_missing_zone(self):
        _baseline("rigid scope")
        iid = _make_inspection("rigid scope", ["distal tip"])

        r = client.post(
            f"/api/inspections/{iid}/supervisor-review",
            headers=AUTH_ADMIN,
            json={
                "agreement": "disagree",
                "rationale": "The uploaded image is actually the o-ring area, not the distal tip, "
                             "and the o-ring area was never actually captured.",
                "image_view_correct": False,
                "corrected_image_view": "o-ring area",
                "missing_zone_correct": False,
                "corrected_missing_zone": "o-ring area",
            },
        )
        assert r.status_code == 201, r.text

        db = SessionLocal()
        try:
            row = (
                db.query(SupervisorReview)
                .filter(SupervisorReview.inspection_id == iid)
                .order_by(SupervisorReview.id.desc())
                .first()
            )
            assert row is not None
            assert row.image_view_correct is False
            assert row.corrected_image_view == "o-ring area"
            assert row.missing_zone_correct is False
            assert row.corrected_missing_zone == "o-ring area"
        finally:
            db.close()
