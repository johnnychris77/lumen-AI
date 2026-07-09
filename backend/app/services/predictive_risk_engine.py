"""v2.4 — Predictive Risk Engine (Clinical Memory, Section 4).

Deterministic heuristic — not a validated predictive model — that turns one
instrument's own recorded history (condition trend, recurring issues, repair
count) into a Low/Moderate/High/Critical likelihood per outcome. Always
carries `human_review_required: true`; never phrased as a certainty.
"""
from __future__ import annotations

from app.services.recurrence_detection_service import CONTAMINATION_TYPES

_LEVELS = ("Low", "Moderate", "High", "Critical")
_LEVEL_RANK = {level: i for i, level in enumerate(_LEVELS)}


def _level_from_count(count: int, thresholds: tuple[int, int, int]) -> str:
    moderate, high, critical = thresholds
    if count >= critical:
        return "Critical"
    if count >= high:
        return "High"
    if count >= moderate:
        return "Moderate"
    return "Low"


def estimate_predictive_risk(condition: dict, recurrence: dict) -> dict:
    """Per-outcome likelihood estimates for one instrument, derived only from
    its own history — never a claim of causation."""
    contamination_repeats = sum(
        count for finding_type, count in recurrence["finding_counts"].items()
        if finding_type in CONTAMINATION_TYPES
    )
    repeat_contamination_likelihood = _level_from_count(contamination_repeats, (2, 4, 6))
    repair_likelihood = _level_from_count(condition["repair_count"], (1, 2, 3))
    supervisor_escalation_likelihood = _level_from_count(recurrence["override_count"], (2, 3, 5))
    declining_bump = 1 if condition["condition_trend"] == "declining" else 0
    removal_from_service_likelihood = _level_from_count(
        condition["repair_count"] + declining_bump, (1, 2, 3)
    )

    overall = max(
        (repeat_contamination_likelihood, repair_likelihood,
         supervisor_escalation_likelihood, removal_from_service_likelihood),
        key=lambda level: _LEVEL_RANK[level],
    )

    return {
        "repeat_contamination_likelihood": repeat_contamination_likelihood,
        "repair_likelihood": repair_likelihood,
        "supervisor_escalation_likelihood": supervisor_escalation_likelihood,
        "removal_from_service_likelihood": removal_from_service_likelihood,
        "overall_risk_level": overall,
        "basis": (
            "Deterministic heuristic derived from this instrument's own recorded "
            "inspection, repair, and override history — a potential association, "
            "not a validated predictive model or a claim of causation."
        ),
        "human_review_required": True,
    }
