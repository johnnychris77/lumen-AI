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


def _identity_tokens(sample: dict, group_by_serial: bool) -> list[str]:
    """The leakage-relevant identity tokens a sample carries. Two samples that
    share ANY token belong in the same split (enforced by union-find in
    ``split_dataset``), so that every image of the same instrument, inspection,
    specimen, capture session, or the same image content itself, is kept
    together. This is stricter than picking a single key by precedence: samples
    that share a specimen but were logged under different inspections are still
    co-located, which single-key grouping would miss.

    An ``instrument_serial`` is only used when ``group_by_serial`` is set (it
    pulls an instrument's whole history out of validation/test). Repeated-image
    content is keyed off ``image_sha256`` so an identical image can never appear
    on both sides of the split and inflate 'independent' validation.
    """
    tokens = list(_real_group_identity_tokens(sample, group_by_serial))
    # Repeated image content — identical bytes must never straddle the split.
    # This is a leakage SAFETY key (it co-locates exact duplicates) but not a
    # real-world grouping identity, so it does not by itself make a cohort's
    # independent validation "reliable" (see ``_real_group_identity_tokens``).
    if sample.get("image_sha256"):
        tokens.append(f"img:{sample['image_sha256']}")
    return tokens


def _real_group_identity_tokens(sample: dict, group_by_serial: bool) -> list[str]:
    """Real-world grouping identities that anchor a sample against same-source
    leakage: instrument (when ``group_by_serial``), inspection, specimen, and
    capture session. A sample with none of these cannot be guaranteed free of
    same-specimen/same-session leakage, however unique its image bytes are."""
    tokens: list[str] = []
    if group_by_serial and sample.get("instrument_serial"):
        tokens.append(f"serial:{sample['instrument_serial']}")
    if sample.get("inspection_id") is not None:
        tokens.append(f"insp:{sample['inspection_id']}")
    specimen = sample.get("specimen_id") or sample.get("provenance_specimen_id")
    if specimen:
        tokens.append(f"spec:{specimen}")
    if sample.get("session_id"):
        tokens.append(f"sess:{sample['session_id']}")
    return tokens


def _group_key(sample: dict, group_by_serial: bool) -> str:
    """Back-compat single-key helper: the first strong identity token, else a
    per-sample fallback. ``split_dataset`` itself now uses union-find over the
    full token set (``_identity_tokens``); this remains for any external caller
    that imported it."""
    tokens = _identity_tokens(sample, group_by_serial)
    return tokens[0] if tokens else f"sample:{sample.get('id')}"


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

    # 1. Union-find: samples that share ANY identity token (instrument serial,
    #    inspection, specimen, session, or identical image content) are merged
    #    into one group, so no such set can straddle the split boundary. A
    #    sample carrying no strong identity token becomes its own singleton
    #    group and is counted as "ungrouped" (see grouping diagnostics below) —
    #    such a cohort cannot support reliable, leakage-free independent
    #    validation, and that is reported rather than silently masked.
    parent: dict[int, int] = {}

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(a: int, b: int) -> None:
        ra, rb = _find(a), _find(b)
        if ra != rb:
            # Attach to the smaller root so a component's key is deterministic.
            parent[max(ra, rb)] = min(ra, rb)

    token_owner: dict[str, int] = {}
    ungrouped_indices: set[int] = set()
    for idx, s in enumerate(samples):
        parent[idx] = idx
        tokens = _identity_tokens(s, group_by_serial)
        # "Ungrouped" (for the reliability signal) means no REAL-WORLD grouping
        # identity — a sha-only sample is still ungrouped in that sense.
        if not _real_group_identity_tokens(s, group_by_serial):
            ungrouped_indices.add(idx)
        for tok in tokens:
            if tok in token_owner:
                _union(idx, token_owner[tok])
            else:
                token_owner[tok] = idx

    # Build connected-component groups. A component's key is its smallest member
    # index (deterministic); its stratum is that of its first sample.
    groups: dict[str, list[dict]] = defaultdict(list)
    group_stratum: dict[str, str] = {}
    for idx, s in enumerate(samples):
        gk = f"grp:{_find(idx)}"
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
    ungrouped_sample_count = len(ungrouped_indices)
    total = len(samples)
    # Independent validation is only trustworthy when every sample is anchored to
    # a real leakage-grouping identity. If some samples carry none (grouped only
    # by their own id), repeated images / same specimen / same session could
    # straddle the split undetected — so this is surfaced honestly rather than
    # reported as a clean, leakage-free split.
    grouping_reliable = total > 0 and ungrouped_sample_count == 0
    return {
        "assignments": assignments,
        "split_groups": split_groups,
        "counts": counts,
        "total_samples": total,
        "total_groups": len(groups),
        "ratios": {TRAIN: train_r, VAL: val_r, TEST: _test_r},
        "group_by_serial": group_by_serial,
        "seed": seed,
        "stratified_by": [
            "instrument_family", "anatomy_zone", "finding",
            "severity", "manufacturer", "image_quality",
        ],
        "grouped_by": ["instrument_serial", "inspection_id", "specimen_id", "session_id", "image_sha256"],
        "ungrouped_sample_count": ungrouped_sample_count,
        "grouping_reliable": grouping_reliable,
        "independent_validation_reliable": grouping_reliable,
    }


def grouping_is_reliable(result: dict) -> bool:
    """True iff every sample was anchored to a real leakage-grouping identity, so
    the split can support leakage-free independent validation. False when any
    sample carried no grouping identity (grouping unsupported for that cohort)."""
    return bool(result.get("grouping_reliable", False))


def has_no_group_leakage(result: dict) -> bool:
    """True iff no group id appears in more than one split (leakage check)."""
    seen: dict[str, str] = {}
    for split, gks in result["split_groups"].items():
        for gk in gks:
            if gk in seen and seen[gk] != split:
                return False
            seen[gk] = split
    return True
