"""Single source of truth for whether an inspection has a VERIFIED AI result.

No trained vision model is deployed in this repository, so a baseline-comparison
(deterministic placeholder) score is NEVER a verified AI clinical result. The
authoritative signal is the persisted ``ai_analysis_status`` on the inspection
row — mirrored from the live-model contract (``ai_analysis.status`` in
``baseline_comparison_scoring_service``):

- ``"COMPLETED"``  → a real promoted model evaluated the image (future state).
- ``"AI_UNAVAILABLE"`` → no eligible model; any stored heuristic score/risk/
  confidence is placeholder and must not be presented as a clinical conclusion.
- ``""`` → a manual (no-image) human entry, or a legacy row written before this
  column existed. Legacy image rows are treated as unavailable (no model has
  ever run), so their stored values are preserved for audit but never presented
  as verified findings.

Raw stored values are kept untouched for audit provenance; these helpers decide
only what may be PRESENTED as a clinical conclusion.
"""
from __future__ import annotations

from typing import Any

AI_VERIFIED_STATUS = "COMPLETED"


def ai_evaluated(row: Any) -> bool:
    """True only when a real, verified AI model evaluated this inspection."""
    return (getattr(row, "ai_analysis_status", "") or "") == AI_VERIFIED_STATUS


def ai_unavailable_for_presentation(row: Any) -> bool:
    """True when an image inspection has no verified AI evaluation — its stored
    heuristic score/risk/confidence/cleaning must NOT be presented as clinical.

    A manual (no-image) entry is a human declaration, not an AI claim, so it is
    not suppressed here (it is simply not 'AI evaluated')."""
    return bool(getattr(row, "has_image", False)) and not ai_evaluated(row)


def evaluation_status(row: Any) -> str:
    """A presentation status: verified AI, AI unavailable, or a manual entry."""
    if ai_evaluated(row):
        return "ai_verified"
    if getattr(row, "has_image", False):
        return "ai_unavailable"
    return "manual_entry"


def presented_inspection_score(row: Any) -> int | None:
    """0–100 quality score to PRESENT, or None when there is no verified AI
    result. Manual no-image entries keep their human-declared score."""
    if ai_unavailable_for_presentation(row):
        return None
    if getattr(row, "score_status", "") in ("scored", "scored_after_override"):
        return 100 - int(getattr(row, "risk_score", 0) or 0)
    return None


def presented_risk_level(row: Any) -> str | None:
    return None if ai_unavailable_for_presentation(row) else getattr(row, "risk_level", None)


def presented_ai_confidence(row: Any) -> float | None:
    return None if ai_unavailable_for_presentation(row) else getattr(row, "ai_confidence", None)


# Text shown in place of a clinical conclusion when AI is unavailable.
UNAVAILABLE_CLEANING = "Manual inspection required — AI analysis unavailable."
UNAVAILABLE_FINDING = "No verified AI observation"
UNAVAILABLE_STATUS_LABEL = "AI unavailable / manual review required"
