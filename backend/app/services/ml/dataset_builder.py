"""Dataset Registry & AI Model Development Foundation — Sections 6 & 7.

Builds a training-ready sample set from the governed dataset registry:
applies the required exclusion filters, reports class/facility/instrument/
manufacturer balance, and hands the eligible samples to the ALREADY-REAL
``app.services.ml.dataset_split.split_dataset`` (leakage-safe, stratified)
rather than reimplementing splitting here. The resulting split assignment is
then written back onto each ``DatasetRegistryEntry`` row.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.dataset_governance import (
    APPROVED,
    ARCHIVED,
    QUALITY_REJECT,
    DatasetRegistryEntry,
)
from app.services.ml.dataset_split import has_no_group_leakage, split_dataset


def _sample_dict(entry: DatasetRegistryEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "inspection_id": entry.inspection_id,
        "instrument_serial": None,
        "instrument_family": entry.instrument_family or "unknown",
        "anatomy_zone": entry.anatomy_zone or "unknown",
        "finding": entry.current_label or "none",
        "severity": "none",
        "manufacturer": entry.manufacturer or "unknown",
        "image_quality": entry.image_quality or "unknown",
    }


def eligible_entries(db: Session, *, tenant_id: str, dataset_version_id: int) -> tuple[list[DatasetRegistryEntry], dict[str, int]]:
    """Apply the required exclusion filters (Section 6) and return the
    eligible entries plus a count of how many were excluded, by reason."""
    all_entries = (
        db.query(DatasetRegistryEntry)
        .filter(
            DatasetRegistryEntry.tenant_id == tenant_id,
            DatasetRegistryEntry.dataset_version_id == dataset_version_id,
        )
        .all()
    )

    # SEC-173-01 (defense in depth): a research-intake image is never training-eligible,
    # independent of any dataset-entry flags. Its lawful basis is private research, not
    # model training; owner attestation authorizes retention, not training use.
    from app.models.retained_image import RetainedImage  # noqa: PLC0415
    from app.services.research_image_authorization_service import RESEARCH_SOURCE  # noqa: PLC0415

    retained_ids = [e.retained_image_id for e in all_entries if e.retained_image_id]
    research_source_ids: set[int] = set()
    if retained_ids:
        research_source_ids = {
            rid
            for (rid,) in db.query(RetainedImage.id).filter(
                RetainedImage.tenant_id == tenant_id,
                RetainedImage.id.in_(retained_ids),
                RetainedImage.source == RESEARCH_SOURCE,
            )
        }

    excluded = Counter()
    seen_sha256: set[str] = set()
    eligible: list[DatasetRegistryEntry] = []
    for entry in all_entries:
        if entry.retained_image_id in research_source_ids:
            excluded["research_source_not_training_eligible"] += 1
            continue
        if entry.review_status == ARCHIVED:
            excluded["archived"] += 1
            continue
        if entry.image_quality == QUALITY_REJECT:
            excluded["rejected_quality"] += 1
            continue
        if entry.phi_verification != "verified":
            excluded["phi_not_verified"] += 1
            continue
        if not entry.training_eligibility:
            excluded["not_marked_training_eligible"] += 1
            continue
        if entry.review_status != APPROVED:
            excluded["not_approved"] += 1
            continue
        if entry.image_sha256 and entry.image_sha256 in seen_sha256:
            excluded["duplicate"] += 1
            continue
        if entry.image_sha256:
            seen_sha256.add(entry.image_sha256)
        eligible.append(entry)

    return eligible, dict(excluded)


def balance_report(entries: list[DatasetRegistryEntry]) -> dict[str, dict[str, int]]:
    """Class/facility/instrument/manufacturer distribution — reported, not
    silently rebalanced, so a reviewer can see and act on any skew."""
    return {
        "by_label": dict(Counter(e.current_label or "unlabeled" for e in entries)),
        "by_facility": dict(Counter(e.facility or "unknown" for e in entries)),
        "by_instrument_family": dict(Counter(e.instrument_family or "unknown" for e in entries)),
        "by_manufacturer": dict(Counter(e.manufacturer or "unknown" for e in entries)),
    }


def build_training_dataset(
    db: Session, *, tenant_id: str, dataset_version_id: int, seed: str = "lumenai-v1", group_by_serial: bool = False,
    persist_split: bool = True,
) -> dict[str, Any]:
    """Build a leakage-safe, filtered training/validation/test dataset from
    the registry (Sections 6 & 7). Persists the resulting split assignment
    back onto each eligible entry unless ``persist_split=False``."""
    eligible, excluded = eligible_entries(db, tenant_id=tenant_id, dataset_version_id=dataset_version_id)
    samples = [_sample_dict(e) for e in eligible]
    split = split_dataset(samples, seed=seed, group_by_serial=group_by_serial)
    leakage_free = has_no_group_leakage(split)

    if persist_split:
        by_id = {e.id: e for e in eligible}
        for sample_id, split_name in split["assignments"].items():
            entry = by_id.get(sample_id)
            if entry is not None:
                entry.split_assignment = split_name
        db.commit()

    return {
        "dataset_version_id": dataset_version_id,
        "eligible_count": len(eligible),
        "excluded": excluded,
        "balance": balance_report(eligible),
        "split": split,
        "leakage_free": leakage_free,
    }
