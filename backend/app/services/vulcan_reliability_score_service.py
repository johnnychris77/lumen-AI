"""Project Vulcan, Section 7: Instrument Reliability Score.

0-100 composite score with a transparent, itemized breakdown. Deliberately
excludes sterilization-cycle counts (the brief's explicit exclusion) --
scoring draws only from real finding/repair/supervisor/baseline evidence.
"""
from __future__ import annotations

from app.models.vulcan_reliability import (
    PROGRESSION_INTERMITTENT,
    PROGRESSION_RAPIDLY_WORSENING,
    PROGRESSION_SLOWLY_WORSENING,
    PROGRESSION_UNRESOLVED,
    REPAIR_OUTCOME_FAILURE_RECURRED,
    REPAIR_OUTCOME_NEW_DEFECT_DETECTED,
    REPAIR_OUTCOME_PARTIALLY_EFFECTIVE,
    REPAIR_OUTCOME_UNABLE_TO_DETERMINE,
    reliability_category,
)

_PROGRESSION_PENALTY = {
    PROGRESSION_RAPIDLY_WORSENING: 25,
    PROGRESSION_SLOWLY_WORSENING: 12,
    PROGRESSION_UNRESOLVED: 15,
    PROGRESSION_INTERMITTENT: 8,
}

_REPAIR_OUTCOME_PENALTY = {
    REPAIR_OUTCOME_FAILURE_RECURRED: 15,
    REPAIR_OUTCOME_NEW_DEFECT_DETECTED: 12,
    REPAIR_OUTCOME_PARTIALLY_EFFECTIVE: 6,
    REPAIR_OUTCOME_UNABLE_TO_DETERMINE: 2,
}


def compute_reliability_score(
    *,
    progression: str,
    recurrence_count: int,
    latest_severity_index: int,
    repair_outcome: str | None = None,
    is_high_risk_zone: bool = False,
    supervisor_concern: bool = False,
    baseline_deviation: bool = False,
    evidence_confidence: str = "moderate",
) -> dict:
    """Section 7: composite score 0-100 with a transparent breakdown.

    Never reads sterilization-cycle counts -- the brief's explicit exclusion.
    """
    breakdown: dict[str, int] = {}

    progression_penalty = _PROGRESSION_PENALTY.get(progression, 0)
    if progression_penalty:
        breakdown["progression"] = -progression_penalty

    recurrence_penalty = min(20, max(0, recurrence_count - 1) * 5)
    if recurrence_penalty:
        breakdown["repeated_findings"] = -recurrence_penalty

    severity_penalty = max(0, latest_severity_index) * 5
    if severity_penalty:
        breakdown["structural_condition"] = -severity_penalty

    repair_penalty = _REPAIR_OUTCOME_PENALTY.get(repair_outcome or "", 0)
    if repair_penalty:
        breakdown["repair_recurrence"] = -repair_penalty

    if is_high_risk_zone:
        breakdown["anatomy_zone_risk"] = -5

    if supervisor_concern:
        breakdown["supervisor_concerns"] = -10

    if baseline_deviation:
        breakdown["baseline_deviation"] = -8

    if evidence_confidence == "low":
        breakdown["evidence_quality"] = -5

    score = 100 + sum(breakdown.values())
    score = max(0, min(100, score))

    return {
        "reliability_score": float(score),
        "reliability_category": reliability_category(score),
        "score_breakdown": breakdown,
    }
