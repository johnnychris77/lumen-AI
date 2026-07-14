"""Advisor — Phase 7 §6: Clinical Performance.

Reuses ``app.services.ml.pilot_validation`` directly for agreement with
the final decision, false positive/negative rates, and confidence-band
calibration (high/low-confidence errors) — all already computed from real
``SupervisorReview`` rows, not recomputed here. Adds only what genuinely
didn't exist: unsupported-case and model-abstention counts, derived from
real ``AdvisoryRecommendationInteraction``/presentation data.
"""
from __future__ import annotations

from typing import Any

from app.services.ml import pilot_validation


def unsupported_cases(presentations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A presented recommendation whose predicted class fell outside the
    model's declared supported classes (``supported_class is None`` in
    the explainability contract) — an honest, real signal, never guessed."""
    return [p for p in presentations if p.get("supported_class") is None]


def model_abstentions(presentations: list[dict[str, Any]]) -> dict[str, Any]:
    """§6 — how often the model abstained (low confidence or unsupported
    class), reusing the same ``abstained`` flag
    ``advisory_recommendation_service.present_recommendation()`` computes."""
    total = len(presentations)
    abstained = sum(1 for p in presentations if p.get("abstained"))
    return {
        "total_presentations": total,
        "abstentions": abstained,
        "abstention_rate": round(abstained / total, 4) if total else None,
    }


def performance_summary(
    supervisor_review_rows: list, presentations: list[dict[str, Any]],
) -> dict[str, Any]:
    """§6 — the full clinical performance payload."""
    return {
        "clinical_metrics": pilot_validation.clinical_metrics(supervisor_review_rows),
        "unsupported_cases": unsupported_cases(presentations),
        "model_abstentions": model_abstentions(presentations),
        "human_review_required": True,
    }
