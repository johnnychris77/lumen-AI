"""Shadow §11 — Safety Monitoring.

Reuses ``app.services.ml.model_tasks.SAFETY_CRITICAL_FINDINGS`` (the same
safety-critical class list Genesis's ``evaluation.safety_metrics()``
already uses) and ``app.services.ml.shadow_failure_analysis`` for repeated
failure patterns, rather than a second definition of either. Adds the
remaining §11 checks that have no existing home: unexpected predictions
(a class the model was never trained to emit), out-of-scope images (image
quality flagged Reject), and unsupported categories (a prediction outside
the model's declared ``supported_classes`` — should never happen per
``app.services.ml.explainability``'s contract, but honestly checked
rather than assumed).
"""
from __future__ import annotations

from typing import Any

from app.services.ml.model_tasks import SAFETY_CRITICAL_FINDINGS
from app.services.ml.shadow_failure_analysis import analyze_failures


def potential_unsafe_recommendations(rows: list) -> list[dict]:
    """A false negative on a safety-critical finding: the AI said
    "no finding" while the human found something dangerous."""
    return [
        {"id": r.id, "inspection_id": r.inspection_id, "predicted_label": r.predicted_label,
         "human_final_label": r.supervisor_final_label}
        for r in rows
        if r.comparison_category == "false_negative" and r.supervisor_final_label in SAFETY_CRITICAL_FINDINGS
    ]


def missed_findings(rows: list) -> list[dict]:
    return [
        {"id": r.id, "inspection_id": r.inspection_id, "human_final_label": r.supervisor_final_label}
        for r in rows if r.comparison_category == "false_negative"
    ]


def unexpected_predictions(rows: list, *, candidate_classes: list[str]) -> list[dict]:
    """A prediction outside the classes this model was actually trained on
    — would indicate a serialization/versioning bug, never expected."""
    return [
        {"id": r.id, "predicted_label": r.predicted_label}
        for r in rows if r.predicted_label and r.predicted_label not in candidate_classes
    ]


def out_of_scope_images(rows: list) -> list[dict]:
    return [
        {"id": r.id, "inspection_id": r.inspection_id, "image_quality": r.image_quality}
        for r in rows if (r.image_quality or "").lower() == "reject"
    ]


def unsupported_categories(rows: list, *, supported_classes: list[str]) -> list[dict]:
    return [
        {"id": r.id, "predicted_label": r.predicted_label}
        for r in rows if r.predicted_label and r.predicted_label not in supported_classes
    ]


def safety_monitor_report(
    rows: list, *, candidate_classes: list[str], supported_classes: list[str], samples: list[dict] | None = None,
) -> dict[str, Any]:
    """§11 — the full safety monitoring report."""
    failures = analyze_failures(samples) if samples else {"ranked_failure_causes": []}
    repeated_patterns = [f for f in failures["ranked_failure_causes"] if f["count"] > 1]

    return {
        "potential_unsafe_recommendations": potential_unsafe_recommendations(rows),
        "missed_findings": missed_findings(rows),
        "repeated_failure_patterns": repeated_patterns,
        "unexpected_predictions": unexpected_predictions(rows, candidate_classes=candidate_classes),
        "out_of_scope_images": out_of_scope_images(rows),
        "unsupported_categories": unsupported_categories(rows, supported_classes=supported_classes),
        "human_review_required": True,
        "note": "No AI output from this program may override a human decision during Shadow Mode.",
    }
