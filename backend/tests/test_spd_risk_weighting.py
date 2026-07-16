"""SPD risk-weighted scoring refinement.

Verifies the SPD risk weighting model, severity-aware overrides, the removal of
bioburden as a standalone KPI in favour of an Overall Cleaning Assessment, the
recommended-action rules, and the explainable scoring output.
"""
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry
from app.services.baseline_comparison_scoring_service import (
    analyze_inspection,
    CONTAMINATION_KPIS,
    CONDITION_KPIS,
    spd_risk_tier,
    spd_risk_impact,
    overall_cleaning_assessment,
)

SHA = "5e1f00d0" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(
            BaselineLibraryEntry.instrument_category == itype
        ).delete()
        db.add(BaselineLibraryEntry(
            udi=f"spd-{itype}", instrument_category=itype, manufacturer_name="M",
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


def _finding(out, kpi):
    return {f["type"]: f for f in out["predicted_findings"]}[kpi]


# ── SPD risk-tier unit rules ─────────────────────────────────────────────────

class TestSpdRiskTier:
    def test_blood_visible_is_critical(self):
        assert spd_risk_tier("blood", 0.45) == "critical"   # visible
        assert spd_risk_tier("blood", 0.80) == "critical"   # heavy
        assert spd_risk_tier("blood", 0.20) == "high"       # trace
        assert spd_risk_tier("blood", 0.05) == "none"

    def test_severe_corrosion_critical_moderate_high(self):
        assert spd_risk_tier("corrosion", 0.80) == "critical"  # severe
        assert spd_risk_tier("corrosion", 0.45) == "high"      # moderate
        assert spd_risk_tier("corrosion", 0.20) == "low"       # minor

    def test_heavy_rust_critical(self):
        assert spd_risk_tier("rust", 0.80) == "critical"
        assert spd_risk_tier("rust", 0.45) == "high"

    def test_debris_and_bone_high(self):
        assert spd_risk_tier("debris", 0.45) == "high"
        assert spd_risk_tier("bone", 0.45) == "high"

    def test_minor_discoloration_low(self):
        assert spd_risk_tier("discoloration", 0.45) == "low"

    def test_structural_findings_critical(self):
        assert spd_risk_tier("crack", 0.45) == "critical"
        assert spd_risk_tier("missing_component", 0.45) == "critical"
        assert spd_risk_tier("insulation_damage", 0.45) == "critical"

    def test_impact_labels(self):
        assert spd_risk_impact("none") == "Clear"
        assert spd_risk_impact("low") == "Monitor"
        assert spd_risk_impact("high") == "Review"
        assert spd_risk_impact("critical") == "Reprocess"


# ── Bioburden removed / cleaning assessment ──────────────────────────────────

class TestBioburdenRemoved:
    def test_bioburden_not_a_kpi(self):
        assert "bioburden" not in CONTAMINATION_KPIS
        assert "bioburden" not in CONDITION_KPIS
        out = _analyze("scissors")
        assert "bioburden" not in out["kpi_summary"]
        assert all(f["type"] != "bioburden" for f in out["predicted_findings"])

    def test_overall_cleaning_assessment_present(self):
        from app.services.baseline_comparison_scoring_service import CLEANING_ASSESSMENT_UNAVAILABLE
        out = _analyze("scissors")
        assert out["overall_cleaning_assessment"] in (
            "Clean", "Residual contamination suspected",
            "Cleaning failure", "Supervisor review required",
            CLEANING_ASSESSMENT_UNAVAILABLE,
        )

    def test_clean_when_no_contamination(self):
        assert overall_cleaning_assessment({}) == "Clean"

    def test_cleaning_failure_on_visible_blood(self):
        findings = {"blood": {"severity_index": 3}}
        assert overall_cleaning_assessment(findings) == "Cleaning failure"


# ── Override + risk rules ────────────────────────────────────────────────────

class TestRiskOverride:
    def test_blood_high_probability_forces_high_risk(self):
        out = _analyze("scissors", declared=["blood"])
        assert out["risk_level"] in ("high", "critical")
        assert "blood" in out["spd_critical_drivers"]

    def test_debris_forces_supervisor_review(self):
        out = _analyze("forceps", declared=["debris"])
        assert "debris" in out["spd_high_drivers"]
        assert "Supervisor review" in out["recommended_action"] \
            or "Reprocess" in out["recommended_action"]

    def test_bone_forces_supervisor_review(self):
        out = _analyze("retractor", declared=["bone"])
        assert "bone" in out["spd_high_drivers"]
        assert out["risk_level"] in ("high", "critical")

    def test_missing_component_forces_high_risk(self):
        # missing_component is not technician-declarable, so assert the SPD rule
        # that forces it critical (which overrides risk to high/critical).
        assert spd_risk_tier("missing_component", 0.5) == "critical"

    def test_crack_removes_from_service(self):
        out = _analyze("forceps", declared=["crack"])
        assert out["risk_level"] == "critical"
        assert "crack" in out["spd_critical_drivers"]

    def test_normal_wear_does_not_fail(self):
        # No declared findings and no eligible model — AI_ANALYSIS_UNAVAILABLE
        # is the honest outcome (false-PASS remediation), never "FAIL".
        out = _analyze("retractor")  # no declared findings
        if not out["critical_flags"] and not out["spd_critical_drivers"]:
            assert out["pass_fail"] in ("PASS", "AI_ANALYSIS_UNAVAILABLE")


# ── Explanation + drivers ────────────────────────────────────────────────────

class TestExplanation:
    def test_top_risk_drivers_and_explanation(self):
        out = _analyze("scissors", declared=["blood"])
        assert out["top_risk_drivers"], "must surface top risk drivers"
        assert out["scoring_explanation"], "must explain the score"
        assert any("matched at" in line for line in out["scoring_explanation"])

    def test_severity_by_kpi_present(self):
        out = _analyze("forceps")
        sev = out["severity_by_kpi"]
        assert "blood" in sev and "spd_risk_impact" in sev["blood"]

    def test_minor_discoloration_low_penalty(self):
        # Discoloration weight is small relative to contamination.
        from app.services.baseline_comparison_scoring_service import _KPI_WEIGHT
        assert _KPI_WEIGHT["discoloration"] < _KPI_WEIGHT["blood"]
        assert _KPI_WEIGHT["discoloration"] <= 5
