"""Governed, research-only anomaly-localization experiment (Stage 5B).

Predefined protocol: VERIFIED-NORMAL images only for fit; a leakage-checked
held-out set for evaluation; pixel/image metrics computed ONLY where valid
reference labels/masks exist; everything research-only and uncalibrated. On
synthetic fixtures the metrics are explicitly flagged as a technical test, not
model performance.
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable

from research.lens_vision.anomaly_contract import build_anomaly_result
from research.lens_vision.anomaly_localization import AnomalyLocalizer, propose_regions
from research.lens_vision.checkpoint import get_record
from research.lens_vision.governance import GT_VERIFIED_NORMAL
from research.lens_vision.provenance import assert_research_authorized


class NormalOnlyViolation(ValueError):
    """A non-verified-normal image was supplied to fit a normal-only model."""


class LeakageError(ValueError):
    """Train and held-out sets share a physical-instrument / specimen / session /
    image identity — independent evaluation would be invalid."""


# ── metrics (pure-python; no sklearn/numpy) ─────────────────────────────────

def auroc(scores: list[float], labels: list[int]) -> float | None:
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else (0.5 if p == n else 0.0)
    return round(wins / (len(pos) * len(neg)), 4)


def average_precision(scores: list[float], labels: list[int]) -> float | None:
    if not scores or sum(labels) == 0:
        return None
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    tp = 0
    fp = 0
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


def dice_iou(pred_mask: list[list[int]], gt_mask: list[list[int]]) -> tuple[float, float]:
    inter = tp = pred = gt = 0
    for pr, gr in zip(pred_mask, gt_mask):
        for a, b in zip(pr, gr):
            pred += a
            gt += b
            if a and b:
                inter += 1
                tp += 1
    dice = (2 * inter) / (pred + gt) if (pred + gt) else 0.0
    union = pred + gt - inter
    iou = inter / union if union else 0.0
    return round(dice, 4), round(iou, 4)


def _identity_tokens(s: dict) -> set[str]:
    toks = set()
    if s.get("instrument_serial"):
        toks.add(f"serial:{s['instrument_serial']}")
    if s.get("inspection_id") is not None:
        toks.add(f"insp:{s['inspection_id']}")
    if s.get("specimen_id"):
        toks.add(f"spec:{s['specimen_id']}")
    if s.get("session_id"):
        toks.add(f"sess:{s['session_id']}")
    if s.get("image_sha256"):
        toks.add(f"img:{s['image_sha256']}")
    return toks


def _real_identity(s: dict) -> bool:
    return any(s.get(k) not in (None, "") for k in ("instrument_serial", "inspection_id", "specimen_id", "session_id"))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = int(round((pct / 100.0) * (len(ordered) - 1)))
    return ordered[max(0, min(k, len(ordered) - 1))]


def run_anomaly_experiment(
    normal_samples: list[dict], test_samples: list[dict], *, config, localizer: AnomalyLocalizer,
    threshold_percentile: float = 97.0, synthetic_technical_test: bool = False,
    allow_approved_clinical: bool = False,
) -> dict[str, Any]:
    """Fit ``localizer`` on verified-normal images and evaluate on held-out data."""
    # Provenance gate on everything.
    assert_research_authorized(normal_samples + test_samples, allow_approved_clinical=allow_approved_clinical)

    # Normal-only integrity: every fit image must be verified-normal.
    for s in normal_samples:
        if s.get("ground_truth_status") != GT_VERIFIED_NORMAL:
            raise NormalOnlyViolation(
                f"Image {s.get('id')} has ground_truth_status "
                f"'{s.get('ground_truth_status')}' — only verified_normal may fit a normal-only model."
            )

    # Leakage: train and held-out must not share any physical/session/image identity.
    train_tokens: set[str] = set()
    for s in normal_samples:
        train_tokens |= _identity_tokens(s)
    for s in test_samples:
        if _identity_tokens(s) & train_tokens:
            raise LeakageError(f"Held-out image {s.get('id')} shares an identity with the training set.")

    all_have_identity = all(_real_identity(s) for s in (normal_samples + test_samples))
    grouping_limitations = [] if all_have_identity else [
        "some samples lack a real grouping identity (instrument/inspection/specimen/session)"
    ]

    record = None
    try:
        record = get_record(config.checkpoint_id) if config.checkpoint_id else None
    except Exception:
        record = None

    # Fit on verified-normal images only.
    localizer.fit([s["image_bytes"] for s in normal_samples])

    results: list[dict] = []
    image_scores: list[float] = []
    image_labels: list[int] = []
    dices: list[float] = []
    ious: list[float] = []
    latencies_ms: list[float] = []

    for s in test_samples:
        t0 = time.perf_counter()
        heatmap, image_score = localizer.score(s["image_bytes"])
        latencies_ms.append(round((time.perf_counter() - t0) * 1000.0, 3))

        flat = [v for row in heatmap for v in row]
        thr = _percentile(flat, threshold_percentile)
        regions = propose_regions(heatmap, threshold=thr, max_regions=5)

        res = build_anomaly_result(
            sample=s, image_score=image_score, heatmap_shape=(len(heatmap), len(heatmap[0]) if heatmap else 0),
            heatmap_ref=f"heatmap://{config.run_id}/{s.get('id')}", regions=regions, config=config,
            record=record, grouping_reliable=all_have_identity, validation_limitations=grouping_limitations,
        )
        results.append(res.to_dict())

        image_scores.append(image_score)
        if "anomaly_label" in s:
            image_labels.append(int(s["anomaly_label"]))
        # Pixel metrics only where a VALID reference mask exists.
        gt_mask = s.get("anomaly_mask")
        if gt_mask is not None:
            pred_mask = [[1 if v >= thr else 0 for v in row] for row in heatmap]
            d, i = dice_iou(pred_mask, gt_mask)
            dices.append(d)
            ious.append(i)

    have_labels = len(image_labels) == len(image_scores) and len(set(image_labels)) > 1
    img_auroc = auroc(image_scores, image_labels) if have_labels else None
    img_ap = average_precision(image_scores, image_labels) if have_labels else None

    pixel_metrics = None
    if dices:
        pixel_metrics = {
            "mean_dice": round(sum(dices) / len(dices), 4),
            "mean_iou": round(sum(ious) / len(ious), 4),
            "n_masked_images": len(dices),
        }

    return {
        "research_only": True,
        "clinical_promotion_eligible": False,
        "localizer": localizer.name,
        "backbone": getattr(localizer, "backbone", ""),
        "checkpoint_id": config.checkpoint_id,
        "synthetic_technical_test": synthetic_technical_test,
        "n_fit_normal": len(normal_samples),
        "n_test": len(test_samples),
        "grouping_reliable": all_have_identity,
        "grouping_limitations": grouping_limitations,
        "image_level_metrics": {
            "auroc": img_auroc, "average_precision": img_ap,
            "measured": have_labels,
            "note": (
                "SYNTHETIC technical test — not model performance." if synthetic_technical_test
                else ("measured on provided labels" if have_labels else "not measured (no valid labels)")
            ),
        },
        "pixel_level_metrics": pixel_metrics or {
            "measured": False, "note": "not measured (no valid reference masks)"
        },
        "latency_ms": {
            "per_image_mean": round(sum(latencies_ms) / len(latencies_ms), 3) if latencies_ms else None,
            "n": len(latencies_ms),
        },
        "results": results,
        "config_fingerprint": config.fingerprint(),
        "note": "RESEARCH ONLY — uncalibrated spatial anomaly signals; not clinical performance.",
    }


def compare_localizers(
    normal_samples: list[dict], test_samples: list[dict], *, config_factory: Callable[[str], Any],
    localizer_factories: dict[str, Callable[[], AnomalyLocalizer]], **kw,
) -> dict[str, Any]:
    """Run several localizers on identical authorized data. A localizer that
    cannot be constructed/fit (e.g. blocked backbone, missing torch/Anomalib) is
    recorded as BLOCKED with the reason — never as fabricated performance."""
    out: dict[str, Any] = {"research_only": True, "comparisons": {}}
    for name, factory in localizer_factories.items():
        try:
            localizer = factory()
            out["comparisons"][name] = run_anomaly_experiment(
                normal_samples, test_samples, config=config_factory(name), localizer=localizer, **kw,
            )
        except Exception as exc:  # blocked path — capture, never fabricate
            out["comparisons"][name] = {
                "status": "blocked", "reason": f"{type(exc).__name__}: {exc}",
                "note": "No performance reported for a blocked localizer.",
            }
    return out


def write_anomaly_model_card(path: str, config, report: dict) -> dict:
    record = None
    try:
        record = get_record(config.checkpoint_id) if config.checkpoint_id else None
    except Exception:
        record = None
    card = {
        "banner": "RESEARCH ONLY — Stage 5B anomaly localization. Uncalibrated, not clinically "
                  "validated, not servable, not promotable. No clinical accuracy claimed.",
        "research_only": True,
        "clinical_promotion_eligible": False,
        "run": config.to_dict(),
        "config_fingerprint": config.fingerprint(),
        "checkpoint": {
            "id": config.checkpoint_id,
            "architecture": getattr(record, "architecture", "") if record else "",
            "digest_sha256": getattr(record, "expected_sha256", "") if record else "",
            "license": getattr(record, "license", "") if record else "",
            "status": ("approved" if (record and record.approved and record.rights_cleared)
                       else ("blocked" if record else "none")),
        },
        "report": report,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2, sort_keys=True, default=str)
    return card
