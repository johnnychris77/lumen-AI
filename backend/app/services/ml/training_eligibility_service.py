"""Project Lens — Section 3: training-eligibility computation.

Anchors eligibility on the Annotation Database's authoritative
`Annotation.ground_truth_status == "ACTIVE"` (Sprint: Annotation Database &
Storage System) rather than the older `DatasetRegistryEntry.review_status`/
`DoubleBlindReview` path `app.services.ml.dataset_builder.eligible_entries()`
uses. `ACTIVE` already requires, structurally, primary+secondary review
agreement or completed clinical adjudication
(`annotation_ground_truth_service.is_eligible_for_ground_truth()`) — so an
eligible Annotation here can never be an unreviewed or AI-only prediction.

Joins to the same governance gates the Project Canvas sprint's
`dataset_eligibility_service`/`dataset_release_service` already established
(rights, quality, PHI, archival, duplicate sha256) via the shared
`DatasetRegistryEntry` both an `Annotation` and a dataset-registry entry
reference through `retained_image_id` — reusing that bridge pattern rather
than inventing a third eligibility mechanism.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models.annotation_database import GROUND_TRUTH_ACTIVE, Annotation
from app.models.dataset_governance import ARCHIVED, QUALITY_REJECT, DatasetRegistryEntry
from app.models.retained_image import RetainedImage
from app.services.observation_taxonomy import (
    NOT_EVALUATED_BY_CURRENT_MODEL,
    OBSERVATION_TAXONOMY,
    canonical_observation_category,
)

MIN_SAMPLES_PER_CLASS = 3

# Categories that are never a Stage C training target — Stage A/B routing
# outcomes, not material identities a classifier is trained to assert.
_NON_TRAINABLE_CATEGORIES = {"insufficient_image_quality"}


def _registry_entry_for(db: Session, *, tenant_id: str, retained_image_id: int) -> DatasetRegistryEntry | None:
    return (
        db.query(DatasetRegistryEntry)
        .filter(
            DatasetRegistryEntry.tenant_id == tenant_id,
            DatasetRegistryEntry.retained_image_id == retained_image_id,
        )
        .order_by(DatasetRegistryEntry.id.desc())
        .first()
    )


def _structural_reason(entry: DatasetRegistryEntry | None) -> str | None:
    """Returns an exclusion reason string, or None if structurally eligible."""
    if entry is None:
        return "no_dataset_registry_entry"
    if entry.review_status == ARCHIVED:
        return "archived"
    if not (entry.usage_rights or "").strip():
        return "rights_restricted"
    if entry.image_quality == QUALITY_REJECT:
        return "rejected_quality"
    if entry.phi_verification != "verified":
        return "phi_not_verified"
    return None


def compute_training_eligibility(db: Session, *, tenant_id: str) -> dict[str, Any]:
    """Compute the real, governed set of images eligible for Project Lens
    training. Returns per-category counts, exclusion reasons, the eligible/
    excluded class split, and the sample dicts training actually consumes.

    Never trains from: unreviewed annotations (ground_truth_status != ACTIVE
    structurally excludes these), rights-restricted images, rejected-quality
    images, PHI-unverified images, archived images, or duplicate image
    content (deduplicated by sha256 below).
    """
    annotations = (
        db.query(Annotation)
        .filter(Annotation.tenant_id == tenant_id, Annotation.ground_truth_status == GROUND_TRUTH_ACTIVE)
        .all()
    )

    excluded_counts: Counter = Counter()
    seen_sha256: set[str] = set()
    samples: list[dict[str, Any]] = []
    provenance_facilities: set[str] = set()

    for ann in annotations:
        entry = _registry_entry_for(db, tenant_id=tenant_id, retained_image_id=ann.retained_image_id)
        reason = _structural_reason(entry)
        if reason is not None:
            excluded_counts[reason] += 1
            continue

        if entry.image_sha256 and entry.image_sha256 in seen_sha256:
            excluded_counts["duplicate"] += 1
            continue

        retained = db.query(RetainedImage).filter(RetainedImage.id == ann.retained_image_id).first()
        if retained is None or not retained.image_bytes:
            excluded_counts["no_retained_image_bytes"] += 1
            continue

        category = canonical_observation_category(ann.primary_observation or "")
        if category not in OBSERVATION_TAXONOMY or category in _NON_TRAINABLE_CATEGORIES:
            excluded_counts["unrecognized_or_non_trainable_category"] += 1
            continue

        if entry.image_sha256:
            seen_sha256.add(entry.image_sha256)
        provenance_facilities.add(entry.facility or "unknown")

        samples.append({
            "id": ann.id,
            "annotation_id": ann.id,
            "retained_image_id": ann.retained_image_id,
            "inspection_id": ann.inspection_id,
            "image_bytes": retained.image_bytes,
            "label": category,
            "instrument_family": entry.instrument_family or "unknown",
            "manufacturer": entry.manufacturer or "unknown",
            "facility": entry.facility or "unknown",
            "anatomy_zone": entry.anatomy_zone or "unknown",
            "image_quality": entry.image_quality or "unknown",
            "image_sha256": entry.image_sha256,
            "digital_twin_id": ann.digital_twin_id or "",
        })

    label_counts = Counter(s["label"] for s in samples)
    eligible_classes = [c for c in OBSERVATION_TAXONOMY if label_counts.get(c, 0) >= MIN_SAMPLES_PER_CLASS
                        and c not in _NON_TRAINABLE_CATEGORIES]
    excluded_classes = [
        c for c in OBSERVATION_TAXONOMY
        if c not in _NON_TRAINABLE_CATEGORIES and c not in eligible_classes
    ]

    # Declared-experimental-run disclosure (Section 3 / FIRST_MODEL_SCOPE.md):
    # any facility name containing this marker identifies synthetic images
    # pushed through the real governed pipeline for this sprint's one
    # declared experimental run — never silently counted as real clinical
    # evidence.
    experimental_marker = "Synthetic Experimental Lab"
    is_experimental = any(experimental_marker in f for f in provenance_facilities) or not provenance_facilities
    data_provenance = "synthetic_experimental" if is_experimental else "real"

    return {
        "tenant_id": tenant_id,
        "total_active_ground_truth_annotations": len(annotations),
        "total_eligible_samples": len(samples),
        "excluded_counts": dict(excluded_counts),
        "label_counts": dict(label_counts),
        "eligible_classes": eligible_classes,
        "excluded_classes": excluded_classes,
        "not_evaluated_marker": NOT_EVALUATED_BY_CURRENT_MODEL,
        "min_samples_per_class": MIN_SAMPLES_PER_CLASS,
        "data_provenance": data_provenance,
        "facilities": sorted(provenance_facilities),
        "samples": samples,
    }


def eligible_samples_by_category(eligibility: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Group the eligibility report's ``samples`` by their (canonical) label
    — a convenience view for reports/tests, not a second computation."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in eligibility["samples"]:
        grouped[s["label"]].append(s)
    return dict(grouped)
