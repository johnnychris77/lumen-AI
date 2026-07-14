"""Shadow §4 — AI Comparison Engine.

Compares a shadow prediction against the locked human ground truth and
classifies the result into exactly one of the six categories §4 requires.
Reuses the same negative-class framing as
``app.services.ml.error_analysis`` (a missed real finding is the more
dangerous error) rather than a second, competing definition of
false-positive/false-negative.
"""
from __future__ import annotations

from app.services.ml.error_analysis import NEGATIVE_LABEL

LOW_CONFIDENCE_THRESHOLD = 0.55

COMPARISON_CATEGORIES = (
    "agreement", "disagreement", "false_positive", "false_negative",
    "low_confidence", "unknown_pattern",
)


def classify_comparison(
    *,
    predicted_label: str | None,
    human_final_label: str | None,
    confidence: float | None,
    negative_label: str = NEGATIVE_LABEL,
    low_confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> str:
    """Classify one shadow prediction against the human final decision.

    Priority: an absent prediction or ground truth is an honest
    ``unknown_pattern`` (nothing to compare); a correct-but-low-confidence
    call is flagged ``low_confidence`` even though it agreed, since a model
    that got lucky at low confidence is still a calibration concern; a
    wrong call is refined into ``false_positive``/``false_negative`` when
    the negative label is on one side, otherwise a generic
    ``disagreement`` (misclassification between two real findings).
    """
    if not predicted_label or not human_final_label:
        return "unknown_pattern"

    agrees = predicted_label == human_final_label
    if agrees:
        if confidence is not None and confidence < low_confidence_threshold:
            return "low_confidence"
        return "agreement"

    if human_final_label == negative_label and predicted_label != negative_label:
        return "false_positive"
    if human_final_label != negative_label and predicted_label == negative_label:
        return "false_negative"
    return "disagreement"
