"""Project Canvas — Section 16: Dataset Eligibility.

A read-only classification of each `DatasetRegistryEntry` into exactly one
of the ten states `app.models.dataset_governance.ELIGIBILITY_*` defines.
Deliberately mirrors, rather than re-derives, the same gates
`app.services.ml.dataset_builder.eligible_entries` already enforces before a
training dataset is built (archived / rejected quality / PHI not verified /
not marked training-eligible / not approved / duplicate sha256) plus the
Section 16 requirement that blank usage rights and a frozen split
assignment are also visible, honest states. There is no UI-settable
override anywhere in this module — every state is computed strictly from
already-governed columns.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.dataset_governance import (
    ADJUDICATED,
    ARCHIVED,
    DISAGREEMENT,
    ELIGIBILITY_ARCHIVED,
    ELIGIBILITY_EXCLUDED,
    ELIGIBILITY_GROUND_TRUTH_APPROVED,
    ELIGIBILITY_NOT_REVIEWED,
    ELIGIBILITY_RESEARCH_ONLY,
    ELIGIBILITY_REVIEW_IN_PROGRESS,
    ELIGIBILITY_RIGHTS_RESTRICTED,
    ELIGIBILITY_TESTING,
    ELIGIBILITY_TRAINING,
    ELIGIBILITY_VALIDATION,
    LABELED,
    QUALITY_REJECT,
    SECOND_REVIEW,
    UNLABELED,
    DatasetRegistryEntry,
)
from app.services.ml.dataset_split import TEST, TRAIN, VAL


def compute_entry_eligibility(entry: DatasetRegistryEntry, *, is_duplicate: bool = False) -> tuple[str, str]:
    """Returns `(state, reason)` for one entry. Order matters — each check
    is a real governance gate, evaluated in the same precedence a human
    reviewer would use (terminal/administrative states first, then the
    review lifecycle, then the training-release gates)."""
    if entry.review_status == ARCHIVED:
        return ELIGIBILITY_ARCHIVED, "Entry has been archived and is retired from active use."
    if not entry.usage_rights.strip():
        return ELIGIBILITY_RIGHTS_RESTRICTED, "No usage-rights record is on file for this image."
    if entry.review_status == UNLABELED:
        return ELIGIBILITY_NOT_REVIEWED, "No annotation review has started for this image."
    if entry.review_status in (LABELED, SECOND_REVIEW, DISAGREEMENT, ADJUDICATED):
        return ELIGIBILITY_REVIEW_IN_PROGRESS, f"Review is in progress (state: {entry.review_status})."
    # entry.review_status == APPROVED from here down — Ground Truth reached.
    if is_duplicate:
        return ELIGIBILITY_EXCLUDED, "Duplicate image content (matching sha256 already registered)."
    if entry.image_quality == QUALITY_REJECT:
        return ELIGIBILITY_EXCLUDED, "Image quality was assessed as Reject."
    if entry.phi_verification != "verified":
        return ELIGIBILITY_EXCLUDED, "PHI verification has not been completed for this image."
    if not entry.training_eligibility:
        return ELIGIBILITY_RESEARCH_ONLY, "Approved but not marked training-eligible; available for research use only."
    if entry.split_assignment == TRAIN:
        return ELIGIBILITY_TRAINING, "Approved, training-eligible, and assigned to the training split."
    if entry.split_assignment == VAL:
        return ELIGIBILITY_VALIDATION, "Approved, training-eligible, and assigned to the validation split."
    if entry.split_assignment == TEST:
        return ELIGIBILITY_TESTING, "Approved, training-eligible, and assigned to the test split."
    return ELIGIBILITY_GROUND_TRUTH_APPROVED, "Ground Truth approved; awaiting dataset-release split assignment."


def compute_registry_eligibility(
    db: Session, *, tenant_id: str, dataset_version_id: int | None = None,
) -> dict[str, Any]:
    query = db.query(DatasetRegistryEntry).filter(DatasetRegistryEntry.tenant_id == tenant_id)
    if dataset_version_id is not None:
        query = query.filter(DatasetRegistryEntry.dataset_version_id == dataset_version_id)
    entries = query.order_by(DatasetRegistryEntry.id.asc()).all()

    sha_counts = Counter(e.image_sha256 for e in entries if e.image_sha256)
    seen_sha256: set[str] = set()

    results = []
    for entry in entries:
        is_duplicate = False
        if entry.image_sha256 and sha_counts[entry.image_sha256] > 1:
            is_duplicate = entry.image_sha256 in seen_sha256
            seen_sha256.add(entry.image_sha256)
        state, reason = compute_entry_eligibility(entry, is_duplicate=is_duplicate)
        results.append({
            "id": entry.id, "lcid": entry.lcid, "eligibility": state, "reason": reason,
            "review_status": entry.review_status, "image_quality": entry.image_quality,
            "usage_rights": entry.usage_rights, "phi_verification": entry.phi_verification,
            "training_eligibility": entry.training_eligibility, "split_assignment": entry.split_assignment,
        })

    return {
        "entries_checked": len(entries),
        "counts": dict(Counter(r["eligibility"] for r in results)),
        "entries": results,
    }
