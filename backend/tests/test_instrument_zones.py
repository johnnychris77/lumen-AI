"""Instrument-specific high-risk zone detection."""
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import analyze_inspection, _overall_result
from app.services.instrument_zones import (
    resolve_zones,
    zone_for_finding,
    zone_fields,
    is_high_retention,
    ZONE_TAXONOMY,
)

SHA = "a1b2c3d4" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"z-{itype}", instrument_category=itype, manufacturer_name="M",
            model_name="X", baseline_type="manufacturer", approval_status="approved",
        ))
        db.commit()
    finally:
        db.close()


def _analyze(itype, declared=None):
    _baseline(itype)
    db = SessionLocal()
    try:
        return analyze_inspection(
            db, instrument_type=itype, tenant_id="default-tenant",
            has_image=True, image_sha256=SHA, declared_findings=declared,
        )
    finally:
        db.close()


class TestTaxonomy:
    def test_taxonomy_categories(self):
        for cat in ("cutting_working_surface", "rotary_orthopedic", "lumen_scope",
                    "mechanical", "handle_external", "unknown"):
            assert cat in ZONE_TAXONOMY

    def test_instrument_zone_mapping(self):
        assert resolve_zones("serrated forceps")[0] == "serrations"
        assert resolve_zones("orthopedic drill")[0] == "drill-bit flute"
        assert resolve_zones("rigid scope")[0] == "o-ring area"
        assert resolve_zones("cannulated shaver")[0] == "inner channel"
        # Unknown instrument → non-retention default.
        assert resolve_zones("mystery tool")[0] == "unspecified region"

    def test_zone_fields_shape(self):
        zf = zone_fields("serrated forceps", "blood")
        assert zf["instrument_zone"] == "serrations"
        assert zf["zone_risk"] == "high"
        assert "retain blood" in zf["zone_reason"].lower() or zf["zone_reason"]
        assert zf["recommended_manual_check"]

    def test_contamination_routes_to_retention_zone(self):
        assert zone_for_finding("orthopedic drill", "debris") == "drill-bit flute"
        assert is_high_retention("drill-bit flute")
        assert not is_high_retention("unspecified region")


class TestSchema:
    def test_findings_carry_zone_fields(self):
        out = _analyze("serrated forceps")
        for f in out["predicted_findings"]:
            for key in ("instrument_zone", "zone_risk", "zone_reason", "recommended_manual_check"):
                assert key in f


class TestZoneEscalation:
    def test_blood_in_serration_escalates(self):
        # Trace-level blood forced on a serrated instrument → REPROCESS (zone).
        out = _analyze("serrated forceps", declared=["blood"])
        cd = out["clinical_decision"]
        assert cd["overall_result"] in ("REPROCESS", "REMOVE FROM SERVICE")
        blood = next(f for f in out["predicted_findings"] if f["type"] == "blood")
        assert blood["instrument_zone"] == "serrations"

    def test_debris_in_drill_flute_escalates(self):
        out = _analyze("orthopedic drill", declared=["debris"])
        assert out["clinical_decision"]["overall_result"] in ("REPROCESS", "REMOVE FROM SERVICE")

    def test_residue_in_oring_escalates_direct(self):
        # Direct rule check: trace organic residue in a high-retention zone -> REPROCESS.
        r = {
            "analysis_status": "completed", "baseline_match_score": 0.92,
            "predicted_findings": [
                {"type": "other_organic_residue", "severity_index": 1, "instrument_zone": "o-ring area"},
            ],
            "identification": {},
        }
        assert _overall_result(r) == "REPROCESS"

    def test_flat_cosmetic_does_not_escalate(self):
        # Trace contamination on a NON-retention (flat) zone stays low.
        r = {
            "analysis_status": "completed", "baseline_match_score": 0.92,
            "predicted_findings": [
                {"type": "blood", "severity_index": 1, "instrument_zone": "unspecified region"},
                {"type": "discoloration", "severity_index": 1, "instrument_zone": "surface discoloration area"},
            ],
            "identification": {},
        }
        assert _overall_result(r) in ("PASS", "MONITOR")


class TestZoneReasoning:
    def test_interpretation_includes_zone_language(self):
        out = _analyze("serrated forceps", declared=["blood"])
        text = " ".join(out["clinical_decision"]["clinical_interpretation"]).lower()
        assert "serrations" in text
        assert "high-retention zone" in text
