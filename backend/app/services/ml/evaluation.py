"""Phase 17 §6 — Evaluation metrics (pure Python, no sklearn).

Computes accuracy, per-class precision/recall/F1, false-positive/negative rates,
a confusion matrix, per-group breakdowns, and — most importantly — the
safety-critical false-negative rates (missed blood/tissue/residue/crack/missing
component). Nothing is fabricated: metrics are computed from provided
(y_true, y_pred) pairs only.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.services.ml.model_tasks import SAFETY_CRITICAL_FINDINGS


def _safe_div(n: float, d: float) -> float | None:
    return round(n / d, 4) if d else None


def confusion_matrix(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, dict[str, int]]:
    m = {t: {p: 0 for p in labels} for t in labels}
    for t, p in zip(y_true, y_pred):
        if t in m and p in m[t]:
            m[t][p] += 1
    return m


def _per_class(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    total = len(y_true)
    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
        tn = total - tp - fp - fn
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = (
            _safe_div(2 * precision * recall, precision + recall)
            if precision is not None and recall is not None and (precision + recall)
            else None
        )
        specificity = _safe_div(tn, tn + fp)
        out[label] = {
            "support": tp + fn,
            "precision": precision,
            "recall": recall,
            # Sensitivity is the clinical synonym for recall (Genesis §5) —
            # exposed under both names so either vocabulary works without
            # recomputing anything.
            "sensitivity": recall,
            "specificity": specificity,
            # PPV/NPV (Shadow §10) — PPV is precision under another name,
            # exposed alongside it; NPV is the specificity-side counterpart
            # precision doesn't cover (TN / (TN + FN)).
            "positive_predictive_value": precision,
            "negative_predictive_value": _safe_div(tn, tn + fn),
            "f1": f1,
            "false_positive_rate": _safe_div(fp, fp + tn),
            "false_negative_rate": _safe_div(fn, fn + tp),
        }
    return out


def evaluate(y_true: list[str], y_pred: list[str], labels: list[str],
             groups: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Full evaluation report.

    ``groups`` optionally maps a breakdown name (e.g. 'instrument_family') to a
    per-sample list of group values (same length as y_true); each is scored
    with accuracy so performance can be read per family / zone / finding / severity.
    """
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must be the same length")
    n = len(y_true)
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    per_class = _per_class(y_true, y_pred, labels)

    # Macro averages over classes that have support.
    supported = [c for c in per_class.values() if c["support"]]
    def _macro(key: str) -> float | None:
        vals = [c[key] for c in supported if c[key] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    breakdowns: dict[str, dict] = {}
    for name, group_vals in (groups or {}).items():
        if len(group_vals) != n:
            continue
        by_group: dict[str, list[bool]] = defaultdict(list)
        for g, t, p in zip(group_vals, y_true, y_pred):
            by_group[g].append(t == p)
        breakdowns[name] = {
            g: {"n": len(hits), "accuracy": _safe_div(sum(hits), len(hits))}
            for g, hits in by_group.items()
        }

    return {
        "sample_count": n,
        "accuracy": _safe_div(correct, n),
        "macro_precision": _macro("precision"),
        "macro_recall": _macro("recall"),
        "macro_f1": _macro("f1"),
        "per_class": per_class,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels),
        "performance_breakdowns": breakdowns,
        "safety_metrics": safety_metrics(y_true, y_pred),
    }


def roc_curve(y_true: list[int], y_scores: list[float]) -> dict[str, Any]:
    """Standard ROC curve (Section 11) for a binary 0/1 ground truth against
    continuous predicted scores — distinct from ``evaluate()`` above, which
    operates on discrete predicted labels. Requires both classes present in
    ``y_true``; otherwise TPR/FPR are undefined and this says so rather than
    fabricating a curve."""
    if len(y_true) != len(y_scores):
        raise ValueError("y_true and y_scores must be the same length")
    total_pos = sum(1 for t in y_true if t == 1)
    total_neg = len(y_true) - total_pos
    if total_pos == 0 or total_neg == 0:
        return {"points": [], "auc": None, "note": "ROC requires both positive and negative examples in y_true."}

    pairs = sorted(zip(y_scores, y_true), key=lambda p: p[0], reverse=True)
    points = [{"threshold": None, "tpr": 0.0, "fpr": 0.0}]
    tp = fp = 0
    prev_score = None
    for score, label in pairs:
        if prev_score is not None and score != prev_score:
            points.append({"threshold": prev_score, "tpr": round(tp / total_pos, 4), "fpr": round(fp / total_neg, 4)})
        if label == 1:
            tp += 1
        else:
            fp += 1
        prev_score = score
    points.append({"threshold": prev_score, "tpr": round(tp / total_pos, 4), "fpr": round(fp / total_neg, 4)})

    return {"points": points, "auc": _trapezoid_auc(points)}


def _trapezoid_auc(points: list[dict[str, float]]) -> float:
    pts = sorted(points, key=lambda p: p["fpr"])
    area = 0.0
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]["fpr"], pts[i - 1]["tpr"]
        x1, y1 = pts[i]["fpr"], pts[i]["tpr"]
        area += (x1 - x0) * (y0 + y1) / 2
    return round(area, 4)


def roc_auc(y_true: list[int], y_scores: list[float]) -> float | None:
    return roc_curve(y_true, y_scores)["auc"]


def pr_curve(y_true: list[int], y_scores: list[float]) -> dict[str, Any]:
    """Precision-recall curve (Section 5) for a binary 0/1 ground truth
    against continuous predicted scores — more informative than ROC when
    the positive class is rare (the common case for contamination/defect
    findings). Requires at least one positive example; otherwise precision
    is undefined and this says so rather than fabricating a curve."""
    if len(y_true) != len(y_scores):
        raise ValueError("y_true and y_scores must be the same length")
    total_pos = sum(1 for t in y_true if t == 1)
    if total_pos == 0:
        return {"points": [], "average_precision": None, "note": "PR curve requires at least one positive example in y_true."}

    pairs = sorted(zip(y_scores, y_true), key=lambda p: p[0], reverse=True)
    points = []
    tp = fp = 0
    prev_score = None
    for score, label in pairs:
        if label == 1:
            tp += 1
        else:
            fp += 1
        if prev_score is not None and score == prev_score:
            points[-1] = {"threshold": score, "precision": round(tp / (tp + fp), 4), "recall": round(tp / total_pos, 4)}
        else:
            points.append({"threshold": score, "precision": round(tp / (tp + fp), 4), "recall": round(tp / total_pos, 4)})
        prev_score = score

    # Average precision: recall-weighted mean of precision at each step where recall increases.
    ap = 0.0
    prev_recall = 0.0
    for pt in points:
        ap += pt["precision"] * (pt["recall"] - prev_recall)
        prev_recall = pt["recall"]

    return {"points": points, "average_precision": round(ap, 4)}


_CALIBRATION_BIN_EDGES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
_OVER_UNDER_CONFIDENCE_GAP = 0.10  # a bin's |confidence - accuracy| beyond this is flagged


def calibration_report(y_correct: list[bool], confidences: list[float], *, target_accuracy: float = 0.8) -> dict[str, Any]:
    """Confidence calibration (Section 7). ``y_correct[i]`` is whether
    prediction i was correct; ``confidences[i]`` is that prediction's
    reported confidence (0-1). Bins predictions into deciles and compares
    each bin's mean confidence to its empirical accuracy — a well-calibrated
    model's confidence approximately equals its accuracy in every bin.
    Empty bins are skipped, never fabricated with an assumed value.
    """
    if len(y_correct) != len(confidences):
        raise ValueError("y_correct and confidences must be the same length")
    if not y_correct:
        return {"bins": [], "expected_calibration_error": None, "recommended_threshold": None,
                "note": "No predictions to calibrate."}

    bins = []
    for i in range(len(_CALIBRATION_BIN_EDGES) - 1):
        lo, hi = _CALIBRATION_BIN_EDGES[i], _CALIBRATION_BIN_EDGES[i + 1]
        idx = [j for j, c in enumerate(confidences) if lo <= c < hi]
        if not idx:
            continue
        mean_conf = sum(confidences[j] for j in idx) / len(idx)
        accuracy = sum(1 for j in idx if y_correct[j]) / len(idx)
        gap = mean_conf - accuracy
        bins.append({
            "range": [lo, min(hi, 1.0)],
            "n": len(idx),
            "mean_confidence": round(mean_conf, 4),
            "empirical_accuracy": round(accuracy, 4),
            "gap": round(gap, 4),
            "over_confident": gap > _OVER_UNDER_CONFIDENCE_GAP,
            "under_confident": gap < -_OVER_UNDER_CONFIDENCE_GAP,
        })

    total = len(confidences)
    ece = sum(b["n"] / total * abs(b["gap"]) for b in bins) if bins else None

    # Recommend the lowest confidence bin's lower edge such that every bin
    # at or above it meets target_accuracy — honestly None if no bin does.
    recommended_threshold = None
    for b in sorted(bins, key=lambda x: x["range"][0]):
        remaining = [rb for rb in bins if rb["range"][0] >= b["range"][0]]
        if all(rb["empirical_accuracy"] >= target_accuracy for rb in remaining):
            recommended_threshold = b["range"][0]
            break

    return {
        "bins": bins,
        "expected_calibration_error": round(ece, 4) if ece is not None else None,
        "over_confident_bins": [b["range"] for b in bins if b["over_confident"]],
        "under_confident_bins": [b["range"] for b in bins if b["under_confident"]],
        "recommended_threshold": recommended_threshold,
        "target_accuracy": target_accuracy,
        "note": (
            "recommended_threshold is null when no confidence range in this evaluation run "
            "achieved the target accuracy — do not substitute a default in that case."
        ),
    }


def safety_metrics(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    """Critical false-negative rates: a missed contamination/defect is the most
    dangerous error in SPD. FNR = missed / actual-present for each critical class."""
    out: dict[str, Any] = {}
    worst = 0.0
    for finding in SAFETY_CRITICAL_FINDINGS:
        present = sum(1 for t in y_true if t == finding)
        missed = sum(1 for t, p in zip(y_true, y_pred) if t == finding and p != finding)
        fnr = _safe_div(missed, present)
        out[f"{finding.replace(' ', '_')}_false_negative_rate"] = fnr
        if fnr is not None:
            worst = max(worst, fnr)
    out["worst_safety_false_negative_rate"] = worst if any(
        v is not None for k, v in out.items()
    ) else None
    out["note"] = (
        "False negatives on contamination/structural findings are the primary "
        "safety risk; these gate promotion (see model_deployment_gates.md)."
    )
    return out
