"""Project Canvas — Section 20: Assignment and Queues.

Read-only aggregation over the already-governed registry/annotation/review
tables — no new assignment model, no fabricated due dates or workload
figures. A record only appears in a queue when the underlying data
genuinely supports it:

  * `unassigned` / `blocked_by_*` come from `DatasetRegistryEntry` plus the
    exact same gates `app.services.ml.dataset_builder.eligible_entries` and
    `app.services.ml.dataset_validation_service.validate_registry` already
    enforce (missing metadata, blank usage rights, rejected image quality)
    — not a second, competing set of rules.
  * `primary_review_due` / `secondary_review_due` / `disagreement` /
    `adjudication_due` / `ground_truth_eligible` come from `Annotation` +
    `AnnotationReview`, using `annotation_ground_truth_service.
    is_eligible_for_ground_truth` for the eligibility check rather than
    re-deriving that rule here.
  * `assigned_to_me` is scoped to what the schema actually records about a
    specific person: annotations the actor personally authored
    (`Annotation.reviewer`) that they have not yet submitted for primary
    review. There is no pre-assignment field for secondary review or
    adjudication in the current schema, so this queue never claims one.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.annotation_database import GROUND_TRUTH_DRAFT, Annotation, AnnotationReview
from app.models.dataset_governance import QUALITY_REJECT, DatasetRegistryEntry
from app.services.annotation_ground_truth_service import is_eligible_for_ground_truth
from app.services.ml.dataset_registry import REQUIRED_STRING_FIELDS, validate_metadata


def _entry_metadata(entry: DatasetRegistryEntry) -> dict[str, str]:
    return {field: getattr(entry, field, "") for field in REQUIRED_STRING_FIELDS}


def _entry_view(entry: DatasetRegistryEntry, **extra: Any) -> dict[str, Any]:
    return {
        "id": entry.id, "lcid": entry.lcid, "instrument_family": entry.instrument_family,
        "manufacturer": entry.manufacturer, "image_type": entry.image_type,
        "review_status": entry.review_status, "image_quality": entry.image_quality,
        "usage_rights": entry.usage_rights, **extra,
    }


def _annotation_view(annotation: Annotation, review: AnnotationReview | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "id": annotation.id, "ann_id": annotation.ann_id, "retained_image_id": annotation.retained_image_id,
        "primary_observation": annotation.primary_observation, "reviewer": annotation.reviewer,
        "ground_truth_status": annotation.ground_truth_status,
        "primary_reviewer": review.primary_reviewer if review else "",
        "secondary_reviewer": review.secondary_reviewer if review else "",
        "agreement": review.agreement if review else None,
        **extra,
    }


def get_queues(db: Session, *, tenant_id: str, actor: str) -> dict[str, Any]:
    entries = db.query(DatasetRegistryEntry).filter(DatasetRegistryEntry.tenant_id == tenant_id).all()
    annotations = db.query(Annotation).filter(Annotation.tenant_id == tenant_id).all()
    reviews = db.query(AnnotationReview).filter(AnnotationReview.tenant_id == tenant_id).all()

    reviews_by_annotation = {r.annotation_id: r for r in reviews}
    annotated_image_ids: set[int] = {a.retained_image_id for a in annotations}

    unassigned: list[dict] = []
    blocked_by_missing_metadata: list[dict] = []
    blocked_by_rights: list[dict] = []
    blocked_by_image_quality: list[dict] = []

    for entry in entries:
        missing = validate_metadata(_entry_metadata(entry))
        if missing:
            blocked_by_missing_metadata.append(_entry_view(entry, missing_fields=missing))
            continue
        if not entry.usage_rights.strip():
            blocked_by_rights.append(_entry_view(entry))
            continue
        if entry.image_quality == QUALITY_REJECT:
            blocked_by_image_quality.append(_entry_view(entry))
            continue
        if entry.retained_image_id not in annotated_image_ids:
            unassigned.append(_entry_view(entry))

    assigned_to_me: list[dict] = []
    primary_review_due: list[dict] = []
    secondary_review_due: list[dict] = []
    disagreement: list[dict] = []
    adjudication_due: list[dict] = []
    ground_truth_eligible: list[dict] = []

    for annotation in annotations:
        review = reviews_by_annotation.get(annotation.id)

        if annotation.reviewer == actor and (review is None or review.primary_submitted_at is None):
            assigned_to_me.append(_annotation_view(annotation, review))

        if review is None or review.primary_submitted_at is None:
            primary_review_due.append(_annotation_view(annotation, review))
            continue

        if review.secondary_submitted_at is None:
            secondary_review_due.append(_annotation_view(annotation, review))
            continue

        if review.agreement is False and review.resolved_at is None:
            disagreement.append(_annotation_view(annotation, review, disagreement_reason=review.disagreement_reason))
            adjudication_due.append(_annotation_view(annotation, review))
            continue

        if annotation.ground_truth_status == GROUND_TRUTH_DRAFT:
            eligible, reason = is_eligible_for_ground_truth(review)
            if eligible:
                ground_truth_eligible.append(_annotation_view(annotation, review, eligibility_reason=reason))

    queues = {
        "unassigned": unassigned,
        "assigned_to_me": assigned_to_me,
        "primary_review_due": primary_review_due,
        "secondary_review_due": secondary_review_due,
        "disagreement": disagreement,
        "adjudication_due": adjudication_due,
        "ground_truth_eligible": ground_truth_eligible,
        "blocked_by_missing_metadata": blocked_by_missing_metadata,
        "blocked_by_rights": blocked_by_rights,
        "blocked_by_image_quality": blocked_by_image_quality,
    }
    return {"counts": {name: len(items) for name, items in queues.items()}, "queues": queues}
