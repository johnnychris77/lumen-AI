"""Project Canvas — Section 10: Blind Secondary Review.

Returns only what a secondary reviewer is allowed to see before they submit
their own independent review: the source image reference, approved
metadata, instrument context, an approved baseline (via
`app.services.baseline_comparison_service`, not fabricated), and the
annotator's own instructions/comments. It never returns any
`AnnotationReview` field — primary label, confidence, comments, or the
computed agreement — enforcing reviewer independence in the backend
itself rather than trusting the frontend to hide it (Section 10's explicit
requirement).
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.annotation_database import Annotation
from app.models.dataset_governance import DatasetRegistryEntry
from app.services import annotation_review_service, baseline_comparison_service


def get_blind_secondary_view(db: Session, *, tenant_id: str, annotation_id: int, actor: str) -> dict[str, Any] | None:
    annotation = (
        db.query(Annotation)
        .filter(Annotation.id == annotation_id, Annotation.tenant_id == tenant_id)
        .first()
    )
    if annotation is None:
        return None

    review = annotation_review_service.get_review(db, tenant_id=tenant_id, annotation_id=annotation_id)
    has_primary = review is not None and review.primary_submitted_at is not None
    already_secondary = review is not None and review.secondary_submitted_at is not None
    is_primary_reviewer = has_primary and actor == review.primary_reviewer

    eligible = has_primary and not already_secondary and not is_primary_reviewer
    if not has_primary:
        blocked_reason = "The primary review has not been submitted yet."
    elif already_secondary:
        blocked_reason = "The secondary review has already been submitted for this annotation."
    elif is_primary_reviewer:
        blocked_reason = "You submitted the primary review for this annotation; a different reviewer must complete the secondary review."
    else:
        blocked_reason = ""

    baseline = None
    dataset_entry = (
        db.query(DatasetRegistryEntry)
        .filter(
            DatasetRegistryEntry.tenant_id == tenant_id,
            DatasetRegistryEntry.retained_image_id == annotation.retained_image_id,
        )
        .first()
    )
    if dataset_entry is not None:
        baseline = baseline_comparison_service.compare_to_baselines(db, tenant_id=tenant_id, entry_id=dataset_entry.id)

    return {
        "annotation_id": annotation.id,
        "ann_id": annotation.ann_id,
        "retained_image_id": annotation.retained_image_id,
        "instrument_family": annotation.instrument_family,
        "instrument_model": annotation.instrument_model,
        "manufacturer": annotation.manufacturer,
        "digital_twin_id": annotation.digital_twin_id,
        "region_type": annotation.region_type,
        "region_coordinates": json.loads(annotation.region_coordinates_json or "[]"),
        "image_quality": annotation.image_quality,
        "annotation_instructions": annotation.comments,
        "baseline": baseline,
        "eligible_to_submit_secondary": eligible,
        "blocked_reason": blocked_reason,
    }
