"""Project Canvas — Section 17: Dataset Release Builder.

A preview/composition layer over already-governed infrastructure — no new
Ground Truth workflow, split algorithm, or export format is introduced
here:

  * Release candidates are Ground-Truth-ACTIVE `Annotation` rows
    (`app.services.annotation_ground_truth_service` is the only path that
    sets that status) whose backing `DatasetRegistryEntry` (joined by
    `retained_image_id`) has cleared the same structural gates
    `app.services.dataset_eligibility_service` already computes
    (quality/PHI/usage-rights/training-eligibility).
  * Distribution, duplicate-group, and leakage-risk previews are computed
    here (read-only) but the actual split assignment is delegated to
    `app.services.ml.dataset_builder.build_training_dataset` and freezing
    to `app.services.ml.dataset_registry.freeze_dataset_version` — both
    already exist and are already routed.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models.annotation_database import GROUND_TRUTH_ACTIVE, Annotation
from app.models.dataset_governance import DatasetRegistryEntry
from app.services.dataset_eligibility_service import compute_entry_eligibility
from app.services.ml.dataset_split import has_no_group_leakage, split_dataset

_RELEASE_READY_STATES = {"ground_truth_approved", "eligible_for_training", "eligible_for_validation", "eligible_for_testing"}


def _release_candidates(db: Session, *, tenant_id: str) -> list[tuple[Annotation, DatasetRegistryEntry]]:
    annotations = (
        db.query(Annotation)
        .filter(Annotation.tenant_id == tenant_id, Annotation.ground_truth_status == GROUND_TRUTH_ACTIVE)
        .order_by(Annotation.id.asc())
        .all()
    )
    pairs: list[tuple[Annotation, DatasetRegistryEntry]] = []
    for annotation in annotations:
        entry = (
            db.query(DatasetRegistryEntry)
            .filter(
                DatasetRegistryEntry.tenant_id == tenant_id,
                DatasetRegistryEntry.retained_image_id == annotation.retained_image_id,
            )
            .first()
        )
        if entry is None:
            continue
        state, _reason = compute_entry_eligibility(entry)
        if state in _RELEASE_READY_STATES:
            pairs.append((annotation, entry))
    return pairs


def build_release_preview(db: Session, *, tenant_id: str) -> dict[str, Any]:
    pairs = _release_candidates(db, tenant_id=tenant_id)

    distribution = {
        "by_label": dict(Counter(a.primary_observation or "unlabeled" for a, _ in pairs)),
        "by_facility": dict(Counter(e.facility or "unknown" for _, e in pairs)),
        "by_manufacturer": dict(Counter(e.manufacturer or "unknown" for _, e in pairs)),
        "by_instrument_family": dict(Counter(e.instrument_family or "unknown" for _, e in pairs)),
    }

    sha_counts = Counter(e.image_sha256 for _, e in pairs if e.image_sha256)
    duplicate_groups = [
        {"image_sha256": sha, "count": count, "entry_ids": [e.id for _, e in pairs if e.image_sha256 == sha]}
        for sha, count in sha_counts.items() if count > 1
    ]

    samples = [
        {
            "id": a.id, "inspection_id": e.inspection_id, "instrument_family": e.instrument_family,
            "anatomy_zone": e.anatomy_zone, "finding": a.primary_observation or "none",
            "severity": a.severity or "none", "manufacturer": e.manufacturer, "image_quality": e.image_quality,
        }
        for a, e in pairs
    ]
    split_preview = split_dataset(samples, seed=f"release-preview-{tenant_id}") if samples else None
    leakage_free = has_no_group_leakage(split_preview) if split_preview else True

    return {
        "candidate_count": len(pairs),
        "candidate_annotation_ids": [a.id for a, _ in pairs],
        "candidate_dataset_entry_ids": [e.id for _, e in pairs],
        "ground_truth_versions": sorted({a.ground_truth_version for a, _ in pairs}),
        "distribution": distribution,
        "duplicate_groups": duplicate_groups,
        "split_preview": {
            "counts": split_preview["counts"] if split_preview else {"train": 0, "validation": 0, "test": 0},
            "leakage_free": leakage_free,
        },
    }
