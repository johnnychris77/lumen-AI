"""Model evaluation framework for the inspection scoring/detection model.

Pure functions to score predictions against ground-truth labels — no model
dependencies — so they work for the current pilot scoring model and for a future
computer-vision model alike. Computes precision, recall, false-positive rate,
false-negative rate, a confusion matrix, and human-reviewer agreement.

These metrics are how we will validate any model before it is allowed to change
a disposition. Critical contamination/damage classes should be tuned for recall
(missing a contaminated/damaged instrument is the costly error). No production
diagnostic-accuracy claims are made by computing these — they are validation
tooling only.
"""
from __future__ import annotations

from typing import Sequence


def confusion_matrix(y_true: Sequence[bool], y_pred: Sequence[bool]) -> dict[str, int]:
    """Return TP/FP/TN/FN counts for a binary (present/absent) class."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must be the same length")
    tp = fp = tn = fn = 0
    for t, p in zip(y_true, y_pred):
        if t and p:
            tp += 1
        elif not t and p:
            fp += 1
        elif not t and not p:
            tn += 1
        else:
            fn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def _safe_div(n: float, d: float) -> float:
    return round(n / d, 4) if d else 0.0


def binary_metrics(y_true: Sequence[bool], y_pred: Sequence[bool]) -> dict:
    """Precision, recall, FPR, FNR, F1, accuracy + confusion matrix for one class."""
    cm = confusion_matrix(y_true, y_pred)
    tp, fp, tn, fn = cm["tp"], cm["fp"], cm["tn"], cm["fn"]
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    fpr = _safe_div(fp, fp + tn)
    fnr = _safe_div(fn, fn + tp)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, tp + fp + tn + fn)
    return {
        "confusion_matrix": cm,
        "precision": precision,
        "recall": recall,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "f1": f1,
        "accuracy": accuracy,
        "support": len(y_true),
    }


def per_class_report(
    y_true: dict[str, Sequence[bool]],
    y_pred: dict[str, Sequence[bool]],
) -> dict[str, dict]:
    """binary_metrics for each KPI class. Keys must match across true/pred."""
    report: dict[str, dict] = {}
    for kpi in y_true:
        if kpi not in y_pred:
            raise ValueError(f"missing predictions for class '{kpi}'")
        report[kpi] = binary_metrics(y_true[kpi], y_pred[kpi])
    return report


def reviewer_agreement(model_labels: Sequence[bool], reviewer_labels: Sequence[bool]) -> dict:
    """Agreement between the model and a human reviewer.

    Returns raw percent agreement and Cohen's kappa (chance-corrected).
    """
    if len(model_labels) != len(reviewer_labels):
        raise ValueError("label sequences must be the same length")
    n = len(model_labels)
    if n == 0:
        return {"percent_agreement": 0.0, "cohen_kappa": 0.0, "n": 0}

    agree = sum(1 for m, r in zip(model_labels, reviewer_labels) if m == r)
    po = agree / n

    # Cohen's kappa
    m_pos = sum(1 for m in model_labels if m) / n
    r_pos = sum(1 for r in reviewer_labels if r) / n
    pe = (m_pos * r_pos) + ((1 - m_pos) * (1 - r_pos))
    kappa = 0.0 if pe >= 1.0 else round((po - pe) / (1 - pe), 4)

    return {"percent_agreement": round(po, 4), "cohen_kappa": kappa, "n": n}
