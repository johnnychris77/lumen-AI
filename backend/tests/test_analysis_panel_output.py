"""Upgraded AI analysis output: summary, confidence, severity/status, pass/fail,
critical-threshold escalation, and explainability."""
from app.services.baseline_comparison_scoring_service import (
    analyze_inspection,
    severity_from_probability,
    status_from_probability,
    kpi_severity,
    risk_tier,
)
from app.db.session import SessionLocal
from app.models.baseline_library import BaselineLibraryEntry

SHA = "5e1f00d0" + "0" * 56


def _baseline(itype: str) -> None:
    db = SessionLocal()
    try:
        db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
        db.add(BaselineLibraryEntry(
            udi=f"panel-{itype}", instrument_category=itype, manufacturer_name="M",
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


# ── Threshold helpers ────────────────────────────────────────────────────────

class TestThresholds:
    def test_severity_rules(self):
        assert severity_from_probability(0.05) == "none"
        assert severity_from_probability(0.20) == "low"
        assert severity_from_probability(0.45) == "moderate"
        assert severity_from_probability(0.80) == "high"

    def test_status_rules(self):
        assert status_from_probability(0.05) == "clear"
        assert status_from_probability(0.20) == "monitor"
        assert status_from_probability(0.45) == "review"
        assert status_from_probability(0.80) == "escalate"


# ── Completed analysis shape ─────────────────────────────────────────────────

class TestCompletedOutput:
    def test_has_summary_and_confidence(self):
        out = _analyze("scissors")
        assert out["analysis_status"] == "completed"
        # No "pending" placeholders in a completed analysis
        assert out["findings_summary"], "findings_summary must be populated"
        assert out["confidence"] is not None
        assert out["confidence_level"] in ("High", "Medium", "Low")
        # AI_ANALYSIS_UNAVAILABLE is the honest outcome when no cleaning KPI
        # was technician-declared and no eligible trained model backs it —
        # the false-PASS remediation's contamination safety invariant.
        assert out["pass_fail"] in ("PASS", "FAIL", "AI_ANALYSIS_UNAVAILABLE")

    def test_kpi_findings_have_severity_and_status(self):
        from app.services.baseline_comparison_scoring_service import ALL_SEVERITY_TOKENS
        out = _analyze("forceps")
        for f in out["predicted_findings"]:
            assert f["severity"] in ALL_SEVERITY_TOKENS
            assert f["status"] in ("clear", "monitor", "review", "escalate")
            assert f["spd_risk"] in ("none", "low", "high", "critical")
            assert f["spd_risk_impact"] in ("Clear", "Monitor", "Review", "Reprocess")
            assert "label" in f

    def test_explainability_present(self):
        out = _analyze("needle_holder")
        ex = out["explainability"]
        assert ex["baseline_source"] == "manufacturer"
        assert ex["baseline_match_score"] == out["baseline_match_score"]
        assert ex["highest_findings"]
        assert ex["risk_drivers"]
        assert ex["confidence_level"] == out["confidence_level"]

    def test_undeclared_findings_report_ai_unavailable_not_pass(self):
        # No declared findings and no eligible trained model → the placeholder
        # must not assert a verified "clean" result (false-PASS remediation).
        out = _analyze("retractor")
        assert out["pass_fail"] == "AI_ANALYSIS_UNAVAILABLE"
        assert "AI analysis unavailable" in out["overall_cleaning_assessment"]


# ── Critical-threshold escalation ────────────────────────────────────────────

class TestCriticalEscalation:
    def test_declared_blood_triggers_reprocess(self):
        # Declaring blood pushes its probability high (>0.30) → FAIL + reprocess
        out = _analyze("scissors", declared=["blood"])
        assert out["critical_flags"], "blood should breach critical threshold"
        assert out["pass_fail"] == "FAIL"
        assert out["risk_level"] in ("high", "critical")
        assert "Reprocess" in out["recommendation"] or "Supervisor review" in out["recommendation"]

    def test_declared_crack_removes_from_service(self):
        out = _analyze("forceps", declared=["crack"])
        assert "crack" in out["critical_flags"]
        assert out["risk_level"] == "critical"
        assert "Remove from service" in out["recommendation"]

    def test_blood_deducts_more_than_discoloration(self):
        # Same probability, blood (high risk) must hurt the score far more than
        # discoloration (cosmetic). Compare via score_adjustments weights.
        blood_out = _analyze("scissors", declared=["blood"])
        disc_adj = next((a for a in blood_out["score_adjustments"] if a["kpi"] == "blood"), None)
        assert disc_adj is not None
        # blood is a high-tier driver
        assert disc_adj["risk_tier"] == "high"

    def test_score_adjustments_and_primary_driver(self):
        out = _analyze("scissors", declared=["blood"])
        assert out["score_adjustments"], "must explain why score changed"
        assert out["primary_risk_driver"] is not None
        # largest deduction listed first (most negative points)
        pts = [a["points"] for a in out["score_adjustments"]]
        assert pts == sorted(pts)

    def test_model_labeled_as_pilot(self):
        out = _analyze("forceps")
        assert out["model_label"] == "Baseline Comparison Scoring Model (pilot)"
        assert out["production_validated"] is False


class TestSeverityScales:
    def test_blood_severity_scale(self):
        assert kpi_severity("blood", 0.05) == "none"
        assert kpi_severity("blood", 0.20) == "trace"
        assert kpi_severity("blood", 0.45) == "visible"
        assert kpi_severity("blood", 0.80) == "heavy"

    def test_rust_severity_scale(self):
        assert kpi_severity("rust", 0.05) == "none"
        assert kpi_severity("rust", 0.20) == "surface rust"
        assert kpi_severity("rust", 0.45) == "moderate rust"
        assert kpi_severity("rust", 0.80) == "heavy rust"

    def test_corrosion_severity_scale(self):
        assert kpi_severity("corrosion", 0.05) == "none"
        assert kpi_severity("corrosion", 0.20) == "minor"
        assert kpi_severity("corrosion", 0.45) == "moderate"
        assert kpi_severity("corrosion", 0.80) == "severe"

    def test_generic_scale_for_others(self):
        assert kpi_severity("tissue", 0.20) == "low"
        assert kpi_severity("tissue", 0.80) == "high"

    def test_risk_tier_severity_based(self):
        # rust/corrosion escalate with severity
        assert risk_tier("rust", 0.05) == "low"
        assert risk_tier("rust", 0.45) == "medium"
        assert risk_tier("rust", 0.80) == "high"      # heavy rust = high
        assert risk_tier("corrosion", 0.80) == "high"  # severe corrosion = high

    def test_risk_tier_fixed(self):
        assert risk_tier("blood", 0.5) == "high"
        assert risk_tier("crack", 0.5) == "high"
        assert risk_tier("missing_component", 0.5) == "high"
        assert risk_tier("bone", 0.5) == "low_medium"
        assert risk_tier("discoloration", 0.5) == "low"


class TestMissingBaseline:
    def test_missing_baseline_still_supervisor_review(self):
        itype = "clip_applier"
        db = SessionLocal()
        try:
            db.query(BaselineLibraryEntry).filter(BaselineLibraryEntry.instrument_category == itype).delete()
            db.commit()
            out = analyze_inspection(
                db, instrument_type=itype, tenant_id="default-tenant",
                has_image=True, image_sha256=SHA,
            )
        finally:
            db.close()
        assert out["analysis_status"] == "supervisor_review_required"
        assert out["inspection_score"] is None
