"""Upgraded AI analysis output: summary, confidence, severity/status, pass/fail,
critical-threshold escalation, and explainability."""
from app.services.baseline_comparison_scoring_service import (
    analyze_inspection,
    severity_from_probability,
    status_from_probability,
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
        assert out["pass_fail"] in ("PASS", "FAIL")

    def test_kpi_findings_have_severity_and_status(self):
        out = _analyze("forceps")
        for f in out["predicted_findings"]:
            assert f["severity"] in ("none", "low", "moderate", "high")
            assert f["status"] in ("clear", "monitor", "review", "escalate")
            assert "label" in f

    def test_explainability_present(self):
        out = _analyze("needle_holder")
        ex = out["explainability"]
        assert ex["baseline_source"] == "manufacturer"
        assert ex["baseline_match_score"] == out["baseline_match_score"]
        assert ex["highest_findings"]
        assert ex["risk_drivers"]
        assert ex["confidence_level"] == out["confidence_level"]

    def test_clean_instrument_passes(self):
        # No declared findings → low probabilities → PASS + accept recommendation
        out = _analyze("retractor")
        if not out["critical_flags"]:
            assert out["pass_fail"] == "PASS"
            assert "Accept inspection" in out["recommendation"]


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
