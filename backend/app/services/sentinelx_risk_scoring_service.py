"""Project Sentinel-X, Sections 3 & 4: SPD Risk Matrix + Dynamic Risk Scoring.

0-100 composite where **higher = more risk** (the inverse convention of
Vulcan's reliability score / Veritas's readiness score, both "higher is
better") -- deliberately so a caller can never mistake one score type for
another. Every factor is real, already-computed signal from another
specialist; nothing here is a fabricated probability.
"""
from __future__ import annotations

from app.models.sentinelx_risk import risk_level, spd_risk_weight_value

_SEVERITY_WEIGHT_MULTIPLIER = 6
_ANATOMY_ZONE_HIGH_RISK_POINTS = 10
_RECURRENCE_POINTS_PER_OCCURRENCE = 5
_RECURRENCE_POINTS_CAP = 25
_DIGITAL_TWIN_TREND_POINTS = {"declining": 20, "insufficient_data": 5, "stable": 0, "improving": -5}
_REPAIR_RECURRENCE_POINTS = 15
_SUPERVISOR_CONCERN_POINTS = 10
_PROCESS_VARIATION_POINTS = 8
_LOW_KNOWLEDGE_CONFIDENCE_POINTS = 10
_UNKNOWN_KNOWLEDGE_CONFIDENCE_POINTS = 5
_LOW_KNOWLEDGE_CONFIDENCE_THRESHOLD = 0.5


def compute_risk_score(
    *, finding_type: str = "", severity_index: int = 0, anatomy_zone_high_risk: bool = False,
    recurrence_count: int = 0, digital_twin_condition_trend: str = "insufficient_data",
    evidence_readiness_score: float | None = None, repair_recurrence: bool = False,
    supervisor_concern: bool = False, knowledge_confidence: float | None = None,
    process_variation_detected: bool = False,
) -> dict:
    """Section 4: composite clinical risk score with a transparent, itemized
    breakdown -- explain every score, per the brief."""
    breakdown: dict[str, float] = {}

    weight_value = spd_risk_weight_value(finding_type) if finding_type else 0
    severity_points = weight_value * max(0, severity_index) * _SEVERITY_WEIGHT_MULTIPLIER
    if severity_points:
        breakdown["finding_severity_and_spd_weight"] = severity_points

    if anatomy_zone_high_risk:
        breakdown["anatomy_zone_risk"] = _ANATOMY_ZONE_HIGH_RISK_POINTS

    recurrence_points = min(_RECURRENCE_POINTS_CAP, recurrence_count * _RECURRENCE_POINTS_PER_OCCURRENCE)
    if recurrence_points:
        breakdown["recurrence"] = recurrence_points

    twin_points = _DIGITAL_TWIN_TREND_POINTS.get(digital_twin_condition_trend, 5)
    if twin_points:
        breakdown["digital_twin_condition"] = twin_points

    if evidence_readiness_score is not None:
        evidence_points = round((100 - evidence_readiness_score) * 0.15, 1)
        if evidence_points:
            breakdown["evidence_readiness_gap"] = evidence_points
    else:
        breakdown["evidence_readiness_gap"] = 10  # no evidence assessment on record is itself a risk factor

    if repair_recurrence:
        breakdown["repair_recurrence"] = _REPAIR_RECURRENCE_POINTS

    if supervisor_concern:
        breakdown["supervisor_concern"] = _SUPERVISOR_CONCERN_POINTS

    if process_variation_detected:
        breakdown["process_variation"] = _PROCESS_VARIATION_POINTS

    if knowledge_confidence is None:
        breakdown["knowledge_confidence"] = _UNKNOWN_KNOWLEDGE_CONFIDENCE_POINTS
    elif knowledge_confidence < _LOW_KNOWLEDGE_CONFIDENCE_THRESHOLD:
        breakdown["knowledge_confidence"] = _LOW_KNOWLEDGE_CONFIDENCE_POINTS

    score = max(0.0, min(100.0, sum(breakdown.values())))

    return {"risk_score": score, "risk_level": risk_level(score), "score_breakdown": breakdown}
