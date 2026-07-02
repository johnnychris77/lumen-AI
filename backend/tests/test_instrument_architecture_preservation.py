"""Instrument architecture preservation patch — anatomy-aware classification,
distinct rigid vs flexible endoscope profiles, zone-weighted scoring, anatomy
profile service, coverage, anatomy-specific mentor wording, and supervisor
anatomy-family feedback.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import analyze_inspection
from app.services.instrument_anatomy import (
    anatomy_profile, get_anatomy, resolve_family,
)
from app.services.inspection_coverage import compute_coverage
from app.services.instrument_zones import zone_fields, is_high_retention

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
            udi=f"arch-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _analyze(itype, inspected_zones=None):
    _baseline(itype)
    db = SessionLocal()
    try:
        return analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant",
            has_image=True, image_sha256=SHA, inspected_zones=inspected_zones,
        )
    finally:
        db.close()


# ── Classification / family differentiation ──────────────────────────────────

class TestClassification:
    def test_rigid_scope_uses_oring_profile(self):
        a = get_anatomy("rigid scope")
        assert resolve_family("rigid scope") == "rigid_scope"
        assert "o-ring area" in a["zone_names"]

    def test_flexible_endoscope_classified_separately_from_rigid(self):
        assert resolve_family("flexible colonoscope") == "flexible_endoscope"
        assert resolve_family("gastroscope") == "flexible_endoscope"
        assert resolve_family("rigid scope") == "rigid_scope"
        a = get_anatomy("flexible bronchoscope")
        assert "biopsy channel" in a["zone_names"]
        assert "suction channel" in a["zone_names"]
        # Flexible endoscope must NOT be reasoned about as an o-ring rigid scope.
        assert "o-ring area" not in a["zone_names"]

    def test_drill_bit_flute_threaded_profile(self):
        assert resolve_family("orthopedic drill bit") == "drill_bit"
        a = get_anatomy("drill bit")
        assert "flutes" in a["zone_names"]
        assert "threaded region" in a["zone_names"]

    def test_kerrison_serration_box_lock_profile(self):
        assert resolve_family("kerrison rongeur") == "kerrison_rongeur"
        a = get_anatomy("kerrison")
        for z in ("serrations", "box lock", "hinge"):
            assert z in a["zone_names"]

    def test_general_forceps_family(self):
        assert resolve_family("kelly forceps") == "general_forceps"

    def test_unknown_instrument_uses_generic_profile_with_warning(self):
        p = anatomy_profile("widget-9000")
        assert p["instrument_family"] == "unknown"
        assert p["profile_found"] is False
        assert p["warning"] and "Supervisor review" in p["warning"]
        # Generic SPD zones are still provided.
        assert p["anatomy_zones"]


# ── Anatomy profile service ───────────────────────────────────────────────────

class TestAnatomyProfileService:
    def test_profile_returns_expected_shape(self):
        p = anatomy_profile("rigid scope", manufacturer="Acme", model="RS-1")
        for key in (
            "instrument_family", "anatomy_zones", "required_zones",
            "high_risk_zones", "zone_descriptions", "contamination_risks",
            "condition_risks", "recommended_image_views", "manual_check_steps",
        ):
            assert key in p
        assert p["manufacturer"] == "Acme"
        assert p["model"] == "RS-1"
        assert p["warning"] is None

    def test_manufacturer_model_hints_help_classification(self):
        # Type is vague but the model name identifies a flexible scope.
        p = anatomy_profile("endoscopic device", model="flexible gastroscope")
        assert p["instrument_family"] == "flexible_endoscope"

    def test_profile_endpoint(self):
        r = client.get("/api/instrument-anatomy/flexible%20colonoscope", headers=AUTH_ADMIN)
        assert r.status_code == 200
        body = r.json()
        assert body["instrument_family"] == "flexible_endoscope"
        assert "biopsy channel" in body["anatomy_zones"]


# ── Zone assignment / zone-aware scoring ──────────────────────────────────────

class TestZoneAwareScoring:
    def test_flexible_endoscope_routes_to_channel_not_oring(self):
        assert zone_fields("flexible gastroscope", "blood")["instrument_zone"] == "biopsy channel"
        assert zone_fields("rigid scope", "blood")["instrument_zone"] == "o-ring area"

    def test_blood_in_hinge_is_high_retention(self):
        zf = zone_fields("curved scissors", "blood")
        assert zf["instrument_zone"] == "hinge"
        assert is_high_retention(zf["instrument_zone"])
        assert zf["zone_risk"] == "high"

    def test_bone_in_drill_flute_is_high_retention(self):
        zf = zone_fields("orthopedic drill", "bone")
        assert zf["instrument_zone"] == "drill-bit flute"
        assert is_high_retention(zf["instrument_zone"])

    def test_residue_in_oring_area_is_high_retention(self):
        zf = zone_fields("rigid scope", "other_organic_residue")
        assert zf["instrument_zone"] == "o-ring area"
        assert is_high_retention(zf["instrument_zone"])

    def test_findings_carry_zone_fields(self):
        result = _analyze("flexible colonoscope")
        for f in result["predicted_findings"]:
            assert "instrument_zone" in f
            assert "zone_risk" in f


# ── Coverage ──────────────────────────────────────────────────────────────────

class TestCoverage:
    def test_missing_required_zone_lowers_coverage(self):
        cov = compute_coverage("kerrison rongeur", ["jaw"])
        assert cov["assessed"] is True
        assert cov["missing"]
        assert cov["overall_coverage"] < 100

    def test_complete_zone_set_improves_coverage(self):
        anatomy = get_anatomy("kerrison rongeur")
        cov = compute_coverage("kerrison rongeur", anatomy["required_images"])
        assert cov["overall_coverage"] == 100
        assert cov["quality"] in ("complete", "acceptable")


# ── Anatomy-specific mentor wording ───────────────────────────────────────────

class TestMentorAnatomyLanguage:
    def test_mentor_uses_flexible_channel_language(self):
        # Force a contamination finding so the mentor speaks to the zone.
        result = _analyze("flexible gastroscope")
        # Inject a channel contamination finding and re-derive the mentor payload.
        from app.services.clinical_mentor import ai_mentor
        result["predicted_findings"] = [{
            "type": "blood", "severity_index": 3, "instrument_zone": "biopsy channel",
            "zone_reason": zone_fields("flexible gastroscope", "blood")["zone_reason"],
            "recommended_manual_check": "Flush and brush the biopsy channel end-to-end.",
        }]
        m = ai_mentor(result, "REPROCESS")
        assert "biopsy channel" in m["where_was_it_detected"]
        assert "channel" in m["why_this_zone_is_high_risk"].lower()


# ── Supervisor anatomy-family feedback ────────────────────────────────────────

class TestSupervisorAnatomyFeedback:
    def test_supervisor_can_correct_instrument_family_and_zone(self):
        # Create an inspection to review.
        _baseline("rigid scope")
        db = SessionLocal()
        try:
            from app.db import models
            insp = models.Inspection(
                tenant_id="default-tenant", file_name="f.jpg", instrument_type="rigid scope",
                risk_score=20, score_status="scored", has_image=True, image_sha256=SHA,
                recommended_action="MONITOR",
            )
            db.add(insp)
            db.commit()
            db.refresh(insp)
            iid = insp.id
        finally:
            db.close()

        r = client.post(
            f"/api/inspections/{iid}/supervisor-review",
            headers=AUTH_ADMIN,
            json={
                "agreement": "disagree",
                "rationale": "This is actually a flexible endoscope, residue is in the biopsy channel.",
                "instrument_family_correct": False,
                "corrected_instrument_family": "flexible endoscope",
                "zone_correct": False,
                "corrected_zone": "biopsy channel",
            },
        )
        assert r.status_code == 201, r.text

        # Verify it persisted as labeled data.
        db = SessionLocal()
        try:
            from app.models.supervisor_review import SupervisorReview
            row = (
                db.query(SupervisorReview)
                .filter(SupervisorReview.inspection_id == iid)
                .order_by(SupervisorReview.id.desc())
                .first()
            )
            assert row is not None
            assert row.instrument_family_correct is False
            assert row.corrected_instrument_family == "flexible endoscope"
            assert row.corrected_zone == "biopsy channel"
        finally:
            db.close()
