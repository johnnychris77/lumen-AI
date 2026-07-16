"""Shadow §10 — Validation Metrics + §14's inspection-volume/performance
readiness evidence.

Wraps ``app.services.ml.evaluation`` (sensitivity/specificity/PPV/NPV/F1/
confusion matrix, calibration_report) rather than recomputing any of it.
Adds two things evaluation.py has no reason to know about: agreement rate
+ inter-reviewer agreement (from ``ShadowGroundTruth``'s two independent
human findings), and ``shadow_go_no_go()`` — the same readiness-gate
philosophy as ``app.services.ml.pilot_validation.go_no_go()``, but scoped
to one candidate model's own reconciled shadow predictions rather than
the deployed placeholder engine's ``SupervisorReview`` rows.
"""
from __future__ import annotations

from typing import Any

from app.services.ml.evaluation import calibration_report, evaluate

MIN_REVIEWS = 30
MIN_AGREEMENT_RATE = 0.80


def _confidence_of(row) -> float | None:
    try:
        return float(row.predicted_confidence)
    except (TypeError, ValueError):
        return None


def validated_metrics(rows: list) -> dict[str, Any]:
    """§10 — full metric suite over this model's reconciled shadow
    predictions: evaluate() (sensitivity/specificity/PPV/NPV/F1/confusion
    matrix) plus calibration_report()."""
    reconciled = [r for r in rows if r.comparison_category]
    y_true = [r.supervisor_final_label for r in reconciled]
    y_pred = [r.predicted_label for r in reconciled]
    labels = sorted(set(y_true) | set(y_pred))
    confidences = [_confidence_of(r) for r in reconciled]
    have_confidence = [
        (correct, conf) for correct, conf in
        ((t == p, c) for t, p, c in zip(y_true, y_pred, confidences)) if conf is not None
    ]

    return {
        "sample_count": len(reconciled),
        "evaluation": evaluate(y_true, y_pred, labels) if reconciled else {},
        "calibration": (
            calibration_report(
                [correct for correct, _ in have_confidence],
                [conf for _, conf in have_confidence],
            )
            if have_confidence else {"bins": [], "expected_calibration_error": None, "note": "No confidence data."}
        ),
        "agreement_rate": round(
            sum(1 for r in reconciled if r.agreed_with_human) / len(reconciled), 4
        ) if reconciled else None,
    }


def inter_reviewer_agreement(ground_truth_rows: list) -> dict[str, Any]:
    """§10 — agreement between the two independent human findings
    (technician vs supervisor) already captured per ``ShadowGroundTruth``
    row, before any adjudication."""
    pairs = [
        (r.technician_finding, r.supervisor_finding) for r in ground_truth_rows
        if r.technician_finding and r.supervisor_finding
    ]
    if not pairs:
        return {"n": 0, "agreement_rate": None, "note": "No paired technician/supervisor findings yet."}
    agreed = sum(1 for t, s in pairs if t == s)
    return {"n": len(pairs), "agreement_rate": round(agreed / len(pairs), 4)}


def shadow_go_no_go(rows: list) -> dict[str, Any]:
    """§14 evidence — inspection-volume and performance-target readiness
    for this candidate model's Validated Candidate promotion, mirroring
    pilot_validation.go_no_go()'s philosophy: never auto-promotes, always
    states exactly what's missing."""
    reconciled = [r for r in rows if r.comparison_category]
    total = len(reconciled)
    agreement = (
        round(sum(1 for r in reconciled if r.agreed_with_human) / total, 4) if total else None
    )

    blocking: list[str] = []
    if total < MIN_REVIEWS:
        blocking.append(f"Insufficient reconciled shadow predictions ({total} < {MIN_REVIEWS}).")
    if agreement is not None and agreement < MIN_AGREEMENT_RATE:
        blocking.append(f"Agreement rate {agreement} below {MIN_AGREEMENT_RATE}.")

    return {
        "decision": "GO" if not blocking else "NO-GO",
        "blocking_issues": blocking,
        "inspection_volume_achieved": total >= MIN_REVIEWS,
        "performance_targets_met": agreement is not None and agreement >= MIN_AGREEMENT_RATE,
        "thresholds": {"min_reviews": MIN_REVIEWS, "min_agreement_rate": MIN_AGREEMENT_RATE},
        "measured": {"total_reconciled": total, "agreement_rate": agreement},
        "human_review_required": True,
    }
