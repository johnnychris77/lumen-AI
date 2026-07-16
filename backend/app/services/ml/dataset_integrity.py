"""Genesis — Section 4: dataset integrity gate.

Unlike ``app.services.ml.dataset_builder.eligible_entries()`` (which
*excludes* duplicates/rejected-quality/archived/unverified images and
continues), this module *rejects the whole dataset* when it fails a
structural integrity check — the candidate training pipeline
(``app.services.ml.candidate_training``) refuses to start training against
an invalid dataset rather than silently training on a degenerate one.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.ml.dataset_split import has_no_group_leakage

MIN_FACILITIES = 2
MIN_MANUFACTURERS = 2
MIN_INSTRUMENT_FAMILIES = 2
MIN_MINORITY_CLASS_RATIO = 0.15  # smallest class must be >= 15% of a split


def check_no_duplicate_images(samples: list[dict[str, Any]]) -> dict[str, Any]:
    hashes = [s["image_sha256"] for s in samples if s.get("image_sha256")]
    counts = Counter(hashes)
    duplicates = {h: n for h, n in counts.items() if n > 1}
    return {"passed": not duplicates, "duplicate_count": sum(duplicates.values()), "duplicate_hashes": list(duplicates)}


def check_diversity(samples: list[dict[str, Any]]) -> dict[str, Any]:
    facilities = {s.get("facility", "unknown") for s in samples}
    manufacturers = {s.get("manufacturer", "unknown") for s in samples}
    instrument_families = {s.get("instrument_family", "unknown") for s in samples}
    return {
        "facility_count": len(facilities),
        "manufacturer_count": len(manufacturers),
        "instrument_family_count": len(instrument_families),
        "facility_passed": len(facilities) >= MIN_FACILITIES,
        "manufacturer_passed": len(manufacturers) >= MIN_MANUFACTURERS,
        "instrument_family_passed": len(instrument_families) >= MIN_INSTRUMENT_FAMILIES,
        "passed": (
            len(facilities) >= MIN_FACILITIES
            and len(manufacturers) >= MIN_MANUFACTURERS
            and len(instrument_families) >= MIN_INSTRUMENT_FAMILIES
        ),
    }


def check_class_balance(samples: list[dict[str, Any]], *, split_name: str = "") -> dict[str, Any]:
    labels = [s.get("label", "unknown") for s in samples]
    counts = Counter(labels)
    if not counts:
        return {"passed": False, "split": split_name, "counts": {}, "reason": "no samples"}
    total = sum(counts.values())
    minority_ratio = min(counts.values()) / total
    return {
        "passed": minority_ratio >= MIN_MINORITY_CLASS_RATIO,
        "split": split_name,
        "counts": dict(counts),
        "minority_ratio": round(minority_ratio, 4),
        "minimum_required_ratio": MIN_MINORITY_CLASS_RATIO,
    }


def validate_dataset(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Pre-split checks: duplicates + facility/manufacturer/instrument
    diversity across the whole eligible sample set."""
    duplicate_check = check_no_duplicate_images(samples)
    diversity_check = check_diversity(samples)
    reasons = []
    if not duplicate_check["passed"]:
        reasons.append(f"{duplicate_check['duplicate_count']} duplicate image(s) found")
    if not diversity_check["facility_passed"]:
        reasons.append(f"only {diversity_check['facility_count']} facilities (need >= {MIN_FACILITIES})")
    if not diversity_check["manufacturer_passed"]:
        reasons.append(f"only {diversity_check['manufacturer_count']} manufacturers (need >= {MIN_MANUFACTURERS})")
    if not diversity_check["instrument_family_passed"]:
        reasons.append(f"only {diversity_check['instrument_family_count']} instrument families (need >= {MIN_INSTRUMENT_FAMILIES})")

    return {
        "valid": not reasons,
        "sample_count": len(samples),
        "duplicate_check": duplicate_check,
        "diversity_check": diversity_check,
        "reasons": reasons,
    }


def validate_split(split_result: dict[str, Any], samples_by_id: dict[Any, dict[str, Any]]) -> dict[str, Any]:
    """Post-split checks: leakage-freedom (reused from Section 7) + balanced
    class distribution within each of train/validation/test."""
    leakage_free = has_no_group_leakage(split_result)
    assignments = split_result["assignments"]

    by_split: dict[str, list[dict]] = {"train": [], "validation": [], "test": []}
    for sample_id, split_name in assignments.items():
        sample = samples_by_id.get(sample_id)
        if sample is not None and split_name in by_split:
            by_split[split_name].append(sample)

    balance_checks = {name: check_class_balance(rows, split_name=name) for name, rows in by_split.items() if rows}
    reasons = []
    if not leakage_free:
        reasons.append("split leakage detected (a group appears in more than one split)")
    for name, check in balance_checks.items():
        if not check["passed"]:
            reasons.append(f"'{name}' split class imbalance: {check['counts']} (minority ratio {check['minority_ratio']} < {MIN_MINORITY_CLASS_RATIO})")

    return {
        "valid": not reasons,
        "leakage_free": leakage_free,
        "balance_checks": balance_checks,
        "reasons": reasons,
    }
