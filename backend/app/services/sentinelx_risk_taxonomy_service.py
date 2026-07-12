"""Project Sentinel-X, Section 2: Risk Taxonomy.

A finding may belong to multiple categories at once -- this returns a list,
never a single enum. Each category is assigned only when a real, already-
computed signal supports it; nothing here is a guess.
"""
from __future__ import annotations

from app.models.sentinelx_risk import (
    RISK_CATEGORY_CLINICAL_QUALITY,
    RISK_CATEGORY_COMPLIANCE,
    RISK_CATEGORY_EDUCATION,
    RISK_CATEGORY_ENTERPRISE,
    RISK_CATEGORY_INSPECTION_QUALITY,
    RISK_CATEGORY_INSTRUMENT_INTEGRITY,
    RISK_CATEGORY_OPERATIONAL,
    RISK_CATEGORY_PATIENT_SAFETY,
    RISK_CATEGORY_WORKFLOW,
    RISK_WEIGHT_HIGHEST,
    spd_risk_weight,
)

_INSTRUMENT_INTEGRITY_FINDINGS = {
    "corrosion", "rust", "crack", "pitting", "missing_component", "damaged_o_ring",
    "insulation_damage", "insulation_breach", "wear", "worn_cutting_edge",
    "loose_joint", "damaged_hinge", "damaged_ratchet",
}


def classify_categories(
    *, finding_type: str = "", evidence_readiness_score: float | None = None,
    digital_twin_condition_trend: str = "insufficient_data", recurrence_count: int = 0,
    repair_recurrence: bool = False, process_variation_detected: bool = False,
    knowledge_confidence: float | None = None,
) -> list[str]:
    categories: set[str] = set()

    if finding_type:
        categories.add(RISK_CATEGORY_CLINICAL_QUALITY)
        if spd_risk_weight(finding_type) == RISK_WEIGHT_HIGHEST:
            categories.add(RISK_CATEGORY_PATIENT_SAFETY)
        if finding_type in _INSTRUMENT_INTEGRITY_FINDINGS:
            categories.add(RISK_CATEGORY_INSTRUMENT_INTEGRITY)

    if digital_twin_condition_trend == "declining":
        categories.add(RISK_CATEGORY_INSTRUMENT_INTEGRITY)

    if evidence_readiness_score is not None and evidence_readiness_score < 75:
        categories.add(RISK_CATEGORY_INSPECTION_QUALITY)
        categories.add(RISK_CATEGORY_COMPLIANCE)

    if process_variation_detected:
        categories.add(RISK_CATEGORY_WORKFLOW)

    if recurrence_count > 0 or repair_recurrence:
        categories.add(RISK_CATEGORY_OPERATIONAL)

    if knowledge_confidence is not None and knowledge_confidence < 0.5:
        categories.add(RISK_CATEGORY_EDUCATION)

    if recurrence_count >= 3:
        categories.add(RISK_CATEGORY_ENTERPRISE)

    return sorted(categories)
