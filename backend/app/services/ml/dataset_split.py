"""Phase 17 §2 — Dataset split with leakage prevention + stratification.

Deterministic 70/15/15 train/validation/test split that:
  * groups samples so images from the same inspection (and baseline/inspection
    pairs, and — if configured — the same instrument serial) never straddle the
    split boundary;
  * stratifies by a composite key (family/zone/finding/severity/manufacturer/
    image-quality) so each split reflects the population.

Pure-Python and deterministic (seeded hashing) — no numpy/sklearn dependency.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

TRAIN, VAL, TEST = "train", "validation", "test"
_DEFAULT_RATIOS = (0.70, 0.15, 0.15)


def _group_key(sample: dict, group_by_serial: bool) -> str:
    """Leakage-prevention grouping key. All samples sharing this key are kept in
    the same split. inspection_id groups an inspection's images (and its
    baseline/inspection pair); optionally the instrument serial groups an
    instrument's whole history out of the validation/test sets."""
    if group_by_serial and sample.get("instrument_serial"):
        return f"serial:{sample['instrument_serial']}"
    if sample.get("inspection_id") is not None:
        return f"insp:{sample['inspection_id']}"
    # Fall back to a per-sample group (its own id) — no grouping constraint.
    return f"sample:{sample.get('id')}"


def _stratum_key(sample: dict) -> str:
    parts = [
        sample.get("instrument_family", "unknown"),
        sample.get("anatomy_zone", "unknown"),
        sample.get("finding", "none"),
        str(sample.get("severity", "none")),
        sample.get("manufacturer", "unknown"),
        sample.get("image_quality", "unknown"),
    ]
    return "|".join(str(p) for p in parts)


def _bucket(group_key: str, seed: str) -> float:
    """Stable [0,1) hash for a group, seeded for reproducibility."""
    h = hashlib.sha256(f"{seed}:{group_key}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def split_dataset(
    samples: list[dict],
    ratios: tuple[float, float, float] = _DEFAULT_RATIOS,
    seed: str = "lumenai-v1",
    group_by_serial: bool = False,
) -> dict[str, Any]:
    """Split samples into train/validation/test.

    Each sample is a dict with (all optional): id, inspection_id,
    instrument_serial, instrument_family, anatomy_zone, finding, severity,
    manufacturer, image_quality.

    Returns assignments (id→split), the grouped sample ids per split, and the
    realized per-stratum counts. Grouping is enforced first (no leakage), then
    groups are distributed within each stratum by a seeded hash to approximate
    the target ratios.
    """
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError(f"ratios must sum to 1.0, got {ratios}")
    train_r, val_r, _test_r = ratios

    # 1. Collect groups and the stratum each group belongs to (a group's stratum
    #    is that of its first sample — grouping wins over stratification to
    #    guarantee no leakage).
    groups: dict[str, list[dict]] = defaultdict(list)
    group_stratum: dict[str, str] = {}
    for s in samples:
        gk = _group_key(s, group_by_serial)
        groups[gk].append(s)
        group_stratum.setdefault(gk, _stratum_key(s))

    # 2. Within each stratum, order groups by their seeded hash and slice by ratio
    #    so every stratum contributes proportionally to all three splits.
    by_stratum: dict[str, list[str]] = defaultdict(list)
    for gk, stratum in group_stratum.items():
        by_stratum[stratum].append(gk)

    assignments: dict[Any, str] = {}
    split_groups: dict[str, list[str]] = {TRAIN: [], VAL: [], TEST: []}
    for stratum, gks in by_stratum.items():
        ordered = sorted(gks, key=lambda g: _bucket(g, seed))
        n = len(ordered)
        n_train = round(n * train_r)
        n_val = round(n * val_r)
        for i, gk in enumerate(ordered):
            if i < n_train:
                split = TRAIN
            elif i < n_train + n_val:
                split = VAL
            else:
                split = TEST
            split_groups[split].append(gk)
            for s in groups[gk]:
                assignments[s.get("id")] = split

    counts = {k: sum(len(groups[g]) for g in v) for k, v in split_groups.items()}
    return {
        "assignments": assignments,
        "split_groups": split_groups,
        "counts": counts,
        "total_samples": len(samples),
        "total_groups": len(groups),
        "ratios": {TRAIN: train_r, VAL: val_r, TEST: _test_r},
        "group_by_serial": group_by_serial,
        "seed": seed,
        "stratified_by": [
            "instrument_family", "anatomy_zone", "finding",
            "severity", "manufacturer", "image_quality",
        ],
    }


def has_no_group_leakage(result: dict) -> bool:
    """True iff no group id appears in more than one split (leakage check)."""
    seen: dict[str, str] = {}
    for split, gks in result["split_groups"].items():
        for gk in gks:
            if gk in seen and seen[gk] != split:
                return False
            seen[gk] = split
    return True
