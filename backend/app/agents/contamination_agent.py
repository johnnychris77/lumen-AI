"""Phase 22 §4 — Contamination Detection Agent.

Owns blood, bone, tissue, organic residue, and debris. Reads the real
inspection's persisted finding (detected_issue/confidence/risk_score) —
it does not run new detection; the underlying scoring already happened in
app/services/baseline_comparison_scoring_service.py before this pipeline
runs on a historical inspection.

Note: the current Inspection schema persists one detected_issue per row
(a future CV release could emit multiple simultaneous findings — see
app/services/ml/feature_store.py) — so `findings` here has at most one
entry today, honestly reflecting what's actually stored.
"""
from __future__ import annotations

from app.agents.context import ContaminationContext, ContaminationFinding
from app.services.clinical_mentor import FINDING_EDUCATION
from app.services.instrument_zones import zone_fields

CONTAMINATION_FINDING_TYPES = {"blood", "bone", "tissue", "debris", "other"}


class ContaminationDetectionAgent:
    NAME = "Contamination Detection Agent"
    VERSION = "1.0.0"
    CAPABILITIES = ["detect_organic_contamination", "assign_contamination_zone", "explain_clinical_significance"]
    DEPENDS_ON = ["InstrumentIntelligenceAgent", "AnatomyIntelligenceAgent"]

    def run(self, instrument_type: str, detected_issue: str, confidence: float, risk_score: int) -> ContaminationContext:
        issue = (detected_issue or "").strip().lower()
        if issue not in CONTAMINATION_FINDING_TYPES:
            return ContaminationContext(findings=[], has_contamination=False)

        zinfo = zone_fields(instrument_type, issue)
        education = FINDING_EDUCATION.get(issue, {})
        severity = "high" if risk_score >= 70 else ("medium" if risk_score >= 40 else "low")

        finding = ContaminationFinding(
            finding_type=issue,
            probability=confidence / 100 if confidence and confidence > 1 else confidence,
            severity=severity,
            confidence=confidence,
            zone=zinfo["instrument_zone"],
            clinical_significance=education.get("clinical_significance", ""),
        )
        return ContaminationContext(findings=[finding], has_contamination=True)
