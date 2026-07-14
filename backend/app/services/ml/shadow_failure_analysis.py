"""Shadow §7 — Failure Analysis.

Reuses ``app.services.ml.error_analysis`` for error-type determination and
the five real-signal root causes it already classifies from (annotation
disagreement, blur, poor lighting, cropping, the anatomy-zone proxy,
model uncertainty). This module only ADDS two refinements to that
classifier's honest ``unknown_pattern`` catch-all, using two NEW real
signals that only exist in the shadow-mode pilot context (never
reclassifying any of the five existing causes, so Genesis's pinned
behavior for those signals is unchanged):

* ``model_limitation`` — the prediction was wrong despite adequate
  confidence (>= the uncertainty threshold) and no other real signal
  explains it: the model itself, not the image or the ground truth, is
  the likely cause.
* ``workflow_issue`` — an explicit, real workflow anomaly was flagged on
  the sample (e.g. the shadow reveal fired before the workflow reached a
  terminal state, or ground truth was missing at reconciliation time).

``unknown_pattern`` remains the final, honest catch-all when neither new
signal applies.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.ml.error_analysis import LOW_CONFIDENCE_THRESHOLD, analyze_errors, classify_error

FAILURE_CAUSES = (
    "poor_image_quality", "ambiguous_anatomy", "annotation_inconsistency",
    "model_limitation", "unknown_pattern", "workflow_issue",
)

# Maps Genesis's root-cause vocabulary onto Shadow §7's requested vocabulary
# (both real, this is presentation only — no reclassification happens).
_CAUSE_ALIASES = {
    "blur": "poor_image_quality",
    "poor_lighting": "poor_image_quality",
    "cropping_or_resolution_issue": "poor_image_quality",
    "incorrect_anatomy": "ambiguous_anatomy",
    "annotation_disagreement": "annotation_inconsistency",
    "model_uncertainty": "model_limitation",
}


def classify_failure(sample: dict[str, Any]) -> dict[str, Any] | None:
    """Classify one sample using error_analysis's real-signal priority
    order, refining only its ``unknown_pattern`` catch-all with the two new
    shadow-specific signals, then relabeling into Shadow §7's vocabulary."""
    error = classify_error(sample)
    if error is None:
        return None
    cause = error["root_cause"]
    if cause == "unknown_pattern":
        if sample.get("workflow_anomaly"):
            cause = "workflow_issue"
        elif (error["confidence"] or 0) >= LOW_CONFIDENCE_THRESHOLD:
            cause = "model_limitation"
    error["failure_classification"] = _CAUSE_ALIASES.get(cause, cause)
    return error


def analyze_failures(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Shadow §7 — classify every failure and rank by frequency and trend.
    Reuses ``analyze_errors``'s totals/error-type counts, then substitutes
    its own ranked failure modes using ``classify_failure``'s relabeled
    causes so §7's exact vocabulary is what gets reported."""
    base = analyze_errors(samples)
    classified = [(s, classify_failure(s)) for s in samples]
    failures = [f for _, f in classified if f is not None]
    cause_counts = Counter(f["failure_classification"] for f in failures)
    ranked = [
        {"failure_cause": cause, "count": count, "share_of_failures": round(count / len(failures), 4)}
        for cause, count in cause_counts.most_common()
    ] if failures else []

    trend: dict[str, int] = {}
    for s, f in classified:
        date = s.get("date")
        if date and f is not None:
            trend[date] = trend.get(date, 0) + 1

    return {
        "total_samples": base["total_samples"],
        "total_failures": base["total_errors"],
        "failure_rate": base["error_rate"],
        "ranked_failure_causes": ranked,
        "frequency_trend": dict(sorted(trend.items())),
        "failures": failures,
    }
