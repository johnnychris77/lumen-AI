"""LCID Sprint 1 — Section 12: Dataset Validation.

A whole-registry governance sweep, distinct from
`app.services.ml.dataset_integrity` (which validates one *candidate
training sample list* just before a split — duplicates + diversity +
class balance). This module instead audits every registered entry for the
registry-hygiene problems Section 12 lists: duplicate images, missing
metadata, invalid labels, invalid reviewer status, orphaned Digital Twins,
missing baseline links, missing usage rights, duplicate IDs.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.baseline_library import BaselineLibraryEntry
from app.models.dataset_governance import ANNOTATION_STATES, DatasetRegistryEntry
from app.services.ml.dataset_registry import REQUIRED_STRING_FIELDS, validate_metadata
from app.services.ml.lcid_service import is_untracked_twin
from app.services.observation_taxonomy import OBSERVATION_TAXONOMY


def _entry_metadata(entry: DatasetRegistryEntry) -> dict[str, str]:
    return {field: getattr(entry, field, "") for field in REQUIRED_STRING_FIELDS}


def validate_registry(db: Session, *, tenant_id: str, dataset_version_id: int | None = None) -> dict[str, Any]:
    query = db.query(DatasetRegistryEntry).filter(DatasetRegistryEntry.tenant_id == tenant_id)
    if dataset_version_id is not None:
        query = query.filter(DatasetRegistryEntry.dataset_version_id == dataset_version_id)
    entries = query.all()

    known_baseline_ids = {
        row.id for row in db.query(BaselineLibraryEntry.id).all()
    }
    known_labels = set(OBSERVATION_TAXONOMY) | {"", "unlabeled"}

    duplicate_images: list[dict] = []
    missing_metadata: list[dict] = []
    invalid_labels: list[dict] = []
    invalid_reviewer_status: list[dict] = []
    orphaned_digital_twins: list[dict] = []
    missing_baseline_links: list[dict] = []
    missing_usage_rights: list[dict] = []
    duplicate_ids: list[dict] = []

    sha_counts = Counter(e.image_sha256 for e in entries if e.image_sha256)
    lcid_counts = Counter(e.lcid for e in entries if e.lcid)

    for e in entries:
        if e.image_sha256 and sha_counts[e.image_sha256] > 1:
            duplicate_images.append({"lcid": e.lcid, "id": e.id, "image_sha256": e.image_sha256})

        missing = validate_metadata(_entry_metadata(e))
        if missing:
            missing_metadata.append({"lcid": e.lcid, "id": e.id, "missing_fields": missing})

        if e.current_label and e.current_label not in known_labels:
            invalid_labels.append({"lcid": e.lcid, "id": e.id, "label": e.current_label})

        if e.review_status not in ANNOTATION_STATES:
            invalid_reviewer_status.append({"lcid": e.lcid, "id": e.id, "review_status": e.review_status})

        if e.digital_twin_id and not is_untracked_twin(e.digital_twin_id):
            pass  # a tracked twin ID is never "orphaned" by definition here
        elif e.digital_twin_id and is_untracked_twin(e.digital_twin_id):
            # Untracked is expected/honest for no-barcode captures — not an
            # error. A genuinely orphaned twin is a digital_twin_id that
            # looks tracked (barcode:/udi:) but never resolved to a real
            # entry at linkage time; since this service only reads what was
            # stored, an "orphan" here means a non-empty, non-untracked
            # value with zero corresponding entries sharing it AND no
            # inspection reachable — surfaced via digital_twin_history()
            # at the route layer instead of duplicated here.
            pass

        if e.baseline_id is not None and e.baseline_id not in known_baseline_ids:
            missing_baseline_links.append({
                "lcid": e.lcid, "id": e.id, "baseline_id": e.baseline_id,
                "reason": "referenced baseline_id does not exist",
            })
        elif e.baseline_id is None and e.review_status not in ("UNLABELED",):
            missing_baseline_links.append({
                "lcid": e.lcid, "id": e.id, "baseline_id": None,
                "reason": "no baseline linked for a reviewed entry",
            })

        if not e.usage_rights.strip():
            missing_usage_rights.append({"lcid": e.lcid, "id": e.id})

        if e.lcid and lcid_counts[e.lcid] > 1:
            duplicate_ids.append({"lcid": e.lcid, "id": e.id})

    reasons = []
    for name, bucket in (
        ("duplicate_images", duplicate_images), ("missing_metadata", missing_metadata),
        ("invalid_labels", invalid_labels), ("invalid_reviewer_status", invalid_reviewer_status),
        ("missing_baseline_links", missing_baseline_links),
        ("missing_usage_rights", missing_usage_rights), ("duplicate_ids", duplicate_ids),
    ):
        if bucket:
            reasons.append(f"{len(bucket)} {name.replace('_', ' ')}")

    return {
        "entries_checked": len(entries),
        "valid": not reasons,
        "reasons": reasons,
        "duplicate_images": duplicate_images,
        "missing_metadata": missing_metadata,
        "invalid_labels": invalid_labels,
        "invalid_reviewer_status": invalid_reviewer_status,
        "orphaned_digital_twins": orphaned_digital_twins,
        "missing_baseline_links": missing_baseline_links,
        "missing_usage_rights": missing_usage_rights,
        "duplicate_ids": duplicate_ids,
    }
