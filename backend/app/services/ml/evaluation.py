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
        out[label] = {
            "support": tp + fn,
            "precision": precision,
            "recall": recall,
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
