"""Calibration + validated evaluation (Stage 5C).

Thresholds are chosen on a DEDICATED calibration set and FROZEN before any
held-out evaluation — never selected per test image. Metrics carry confidence
intervals; proportions use the Wilson interval and AUROC uses a deterministic
bootstrap. Severity is never inferred from anomaly scores; synthetic fixtures are
never reported as clinical accuracy.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


# ── primitives ──────────────────────────────────────────────────────────────

def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = min(len(ordered) - 1, max(0, int(round(q * (len(ordered) - 1)))))
    return float(ordered[k])


def auroc(scores: list[float], labels: list[int]) -> float | None:
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return None
    wins = sum((1.0 if p > n else 0.5 if p == n else 0.0) for p in pos for n in neg)
    return round(wins / (len(pos) * len(neg)), 4)


def average_precision(scores: list[float], labels: list[int]) -> float | None:
    if not scores or sum(labels) == 0:
        return None
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    tp = fp = 0
    total_pos = sum(labels)
    ap = 0.0
    prev_recall = 0.0
    for i in order:
        if labels[i] == 1:
            tp += 1
        else:
            fp += 1
        precision = tp / (tp + fp)
        recall = tp / total_pos
        ap += precision * (recall - prev_recall)
        prev_recall = recall
    return round(ap, 4)


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Wilson score CI for a proportion k/n."""
    if n == 0:
        return None
    phat = k / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = (z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)) / denom
    return (round(max(0.0, center - half), 4), round(min(1.0, center + half), 4))


def bootstrap_auroc_ci(scores: list[float], labels: list[int], *, n_boot: int = 300, seed: int = 1337):
    base = auroc(scores, labels)
    if base is None:
        return None
    rng = random.Random(seed)
    n = len(scores)
    vals = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        a = auroc([scores[i] for i in idx], [labels[i] for i in idx])
        if a is not None:
            vals.append(a)
    if not vals:
        return None
    vals.sort()
    return (round(vals[int(0.025 * (len(vals) - 1))], 4), round(vals[int(0.975 * (len(vals) - 1))], 4))


def dice_iou(pred_mask: list[list[int]], gt_mask: list[list[int]]) -> tuple[float, float]:
    inter = pred = gt = 0
    for pr, gr in zip(pred_mask, gt_mask):
        for a, b in zip(pr, gr):
            pred += a
            gt += b
            if a and b:
                inter += 1
    dice = (2 * inter) / (pred + gt) if (pred + gt) else 0.0
    union = pred + gt - inter
    iou = inter / union if union else 0.0
    return round(dice, 4), round(iou, 4)


# ── frozen threshold ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FrozenThreshold:
    image_threshold: float
    pixel_threshold: float
    method: str
    target_fpr: float
    n_calibration: int
    frozen: bool = True

    def to_dict(self) -> dict:
        return {
            "image_threshold": self.image_threshold, "pixel_threshold": self.pixel_threshold,
            "method": self.method, "target_fpr": self.target_fpr,
            "n_calibration": self.n_calibration, "frozen": self.frozen,
        }


def fit_frozen_threshold(
    calibration_image_scores: list[float], calibration_pixel_scores: list[float], *, target_fpr: float = 0.05,
) -> FrozenThreshold:
    """Freeze image- and pixel-level thresholds at the (1 - target_fpr) quantile of
    NORMAL calibration scores. Computed ONCE, before held-out evaluation."""
    if not calibration_image_scores:
        raise ValueError("A non-empty calibration set of NORMAL images is required to freeze a threshold.")
    q = 1.0 - target_fpr
    return FrozenThreshold(
        image_threshold=quantile(calibration_image_scores, q),
        pixel_threshold=quantile(calibration_pixel_scores, q) if calibration_pixel_scores else float("inf"),
        method=f"normal_calibration_quantile(q={q})",
        target_fpr=target_fpr,
        n_calibration=len(calibration_image_scores),
    )


def classification_metrics(scores: list[float], labels: list[int], threshold: float) -> dict:
    """Point metrics at a FROZEN threshold, with Wilson CIs."""
    tp = fp = tn = fn = 0
    for s, y in zip(scores, labels):
        pred = 1 if s >= threshold else 0
        if pred and y:
            tp += 1
        elif pred and not y:
            fp += 1
        elif not pred and y:
            fn += 1
        else:
            tn += 1
    def _ratio(k, n):
        return round(k / n, 4) if n else None
    return {
        "threshold": round(threshold, 6),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": _ratio(tp, tp + fp), "precision_ci95": wilson_interval(tp, tp + fp),
        "recall_sensitivity": _ratio(tp, tp + fn), "recall_ci95": wilson_interval(tp, tp + fn),
        "specificity": _ratio(tn, tn + fp), "specificity_ci95": wilson_interval(tn, tn + fp),
        "false_negative_rate": _ratio(fn, tp + fn),
        "false_positive_rate": _ratio(fp, fp + tn),
    }
