"""Genesis — Section 6: automated error classification and ranked failure modes.

Every root cause here is attributed from a REAL, already-available signal —
never guessed:

  * ``annotation_disagreement`` — from ``DoubleBlindReview.agreement is False``
    for that image (the ground truth itself was disputed, not necessarily a
    model error).
  * ``blur`` / ``poor_lighting`` / ``cropping_or_resolution_issue`` — from
    the real, pixel-computed ``ImageQualityAssessment`` flags
    (``app.services.ml.image_quality``).
  * ``incorrect_anatomy`` — proxied from the image's anatomy zone not being
    identified (``anatomy_zone`` blank/unknown); this is a real, checkable
    proxy, not a true anatomy-classifier disagreement (no such classifier's
    ground truth is available per-sample) — documented as a proxy in
    ``docs/ml-governance/ERROR_ANALYSIS.md``.
  * ``model_uncertainty`` — the model's own reported confidence was below
    threshold.
  * ``unknown_pattern`` — the honest catch-all when no other real signal
    explains the error.

Each error also gets an ``error_type`` (false_positive / false_negative /
misclassification_between_findings), using "no_actionable_finding" as the
negative class — a missed real finding (false_negative) is flagged as the
more dangerous error, consistent with ``app.services.ml.evaluation.
safety_metrics``.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

NEGATIVE_LABEL = "no_actionable_finding"
LOW_CONFIDENCE_THRESHOLD = 0.55

ROOT_CAUSES = (
    "annotation_disagreement", "blur", "poor_lighting", "cropping_or_resolution_issue",
    "incorrect_anatomy", "model_uncertainty", "unknown_pattern",
)


def _error_type(true_label: str, predicted_label: str) -> str:
    if true_label == NEGATIVE_LABEL and predicted_label != NEGATIVE_LABEL:
        return "false_positive"
    if true_label != NEGATIVE_LABEL and predicted_label == NEGATIVE_LABEL:
        return "false_negative"
    return "misclassification_between_findings"


def _root_cause(sample: dict[str, Any]) -> str:
    if sample.get("annotation_disagreement"):
        return "annotation_disagreement"
    if sample.get("blur_flag") or sample.get("focus_flag"):
        return "blur"
    if sample.get("lighting_flag") or sample.get("exposure_flag"):
        return "poor_lighting"
    if sample.get("cropping_flag"):
        return "cropping_or_resolution_issue"
    if not sample.get("anatomy_zone"):
        return "incorrect_anatomy"
    confidence = sample.get("confidence")
    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        return "model_uncertainty"
    return "unknown_pattern"


def classify_error(sample: dict[str, Any]) -> dict[str, Any] | None:
    """Classify one sample's prediction. Returns ``None`` if the prediction
    was correct (not an error)."""
    true_label = sample.get("true_label")
    predicted_label = sample.get("predicted_label")
    if true_label == predicted_label:
        return None
    return {
        "id": sample.get("id"),
        "true_label": true_label,
        "predicted_label": predicted_label,
        "confidence": sample.get("confidence"),
        "error_type": _error_type(true_label, predicted_label),
        "root_cause": _root_cause(sample),
    }


def analyze_errors(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify every error in ``samples`` and rank failure modes by
    frequency. Each ``sample`` dict: ``{id, true_label, predicted_label,
    confidence, blur_flag, focus_flag, lighting_flag, exposure_flag,
    cropping_flag, anatomy_zone, annotation_disagreement}`` (all optional
    except the two labels)."""
    errors = [e for e in (classify_error(s) for s in samples) if e is not None]
    error_type_counts = Counter(e["error_type"] for e in errors)
    root_cause_counts = Counter(e["root_cause"] for e in errors)

    ranked_failure_modes = [
        {"root_cause": cause, "count": count, "share_of_errors": round(count / len(errors), 4)}
        for cause, count in root_cause_counts.most_common()
    ] if errors else []

    return {
        "total_samples": len(samples),
        "total_errors": len(errors),
        "error_rate": round(len(errors) / len(samples), 4) if samples else None,
        "error_type_counts": dict(error_type_counts),
        "ranked_failure_modes": ranked_failure_modes,
        "errors": errors,
    }
