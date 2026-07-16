"""Shadow §5 — Performance Dashboard.

Computed entirely from reconciled ``ShadowPrediction`` rows (i.e. rows
whose ``comparison_category`` has been set by the reveal gate) for one
candidate model — distinct from ``app.services.ml.pilot_validation.
dashboard()``, which reports the already-deployed placeholder scoring
engine's agreement from ``SupervisorReview`` rows. Reuses
``app.services.ml.evaluation.evaluate()`` for per-class metrics and group
breakdowns rather than a second confusion-matrix implementation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.services.ml.evaluation import evaluate

_CONFIDENCE_BUCKETS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]


def _confidence_of(row) -> float | None:
    try:
        return float(row.predicted_confidence)
    except (TypeError, ValueError):
        return None


def _reconciled(rows: list) -> list:
    return [r for r in rows if r.comparison_category]


def confidence_distribution(rows: list) -> dict[str, int]:
    buckets = {f"{lo}-{hi}": 0 for lo, hi in _CONFIDENCE_BUCKETS}
    for r in rows:
        c = _confidence_of(r)
        if c is None:
            continue
        for lo, hi in _CONFIDENCE_BUCKETS:
            if lo <= c < hi:
                buckets[f"{lo}-{hi}"] += 1
                break
    return buckets


def trend_over_time(rows: list) -> dict[str, dict[str, Any]]:
    """Agreement rate per calendar day the prediction was revealed."""
    by_day: dict[str, list] = defaultdict(list)
    for r in rows:
        if r.revealed_at is None:
            continue
        by_day[r.revealed_at.date().isoformat()].append(r)
    return {
        day: {
            "n": len(day_rows),
            "agreement_rate": round(
                sum(1 for r in day_rows if r.agreed_with_human) / len(day_rows), 4
            ) if day_rows else None,
        }
        for day, day_rows in sorted(by_day.items())
    }


def _group_accuracy(rows: list, attr: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        key = getattr(r, attr, "") or "unspecified"
        groups[key].append(r)
    return {
        key: {
            "n": len(g),
            "agreement_rate": round(sum(1 for r in g if r.agreed_with_human) / len(g), 4) if g else None,
        }
        for key, g in groups.items()
    }


def performance_dashboard(rows: list) -> dict[str, Any]:
    """§5 — the full pilot performance dashboard payload for one candidate
    model's shadow predictions."""
    reconciled = _reconciled(rows)
    y_true = [r.supervisor_final_label for r in reconciled]
    y_pred = [r.predicted_label for r in reconciled]
    labels = sorted(set(y_true) | set(y_pred))
    per_class_performance = evaluate(y_true, y_pred, labels)["per_class"] if reconciled else {}

    category_counts = Counter(r.comparison_category for r in reconciled)

    return {
        "total_inspections": len(rows),
        "total_reconciled": len(reconciled),
        "agreement_rate": round(
            sum(1 for r in reconciled if r.agreed_with_human) / len(reconciled), 4
        ) if reconciled else None,
        "per_class_performance": per_class_performance,
        "false_positives": category_counts.get("false_positive", 0),
        "false_negatives": category_counts.get("false_negative", 0),
        "low_confidence_agreements": category_counts.get("low_confidence", 0),
        "unknown_pattern": category_counts.get("unknown_pattern", 0),
        "confidence_distribution": confidence_distribution(reconciled),
        "trend_over_time": trend_over_time(reconciled),
        "performance_by_facility": _group_accuracy(reconciled, "facility_id"),
        "performance_by_instrument": _group_accuracy(reconciled, "instrument_family"),
        "performance_by_anatomy_zone": _group_accuracy(reconciled, "anatomy_zone"),
        "performance_by_image_quality": _group_accuracy(reconciled, "image_quality"),
        "human_review_required": True,
        "note": "Shadow-mode evidence only; the AI never drove or influenced any of these decisions.",
    }
