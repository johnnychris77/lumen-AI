"""Annotation Database — Section 5: Multi-Reviewer Workflow.

Primary + independent secondary reviewer, plus clinical adjudication when
they disagree. Structurally mirrors
`app.services.ml.double_blind_review` (built for `DatasetRegistryEntry`)
but scoped to one `Annotation` row, since a single image may carry several
distinct annotations each needing independent review.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.annotation_database import ROLES_MAY_FINALIZE_GROUND_TRUTH, ROLES_MAY_REVIEW, AnnotationReview
from app.services.enterprise_audit_service import record_enterprise_audit_event


class ReviewAlreadySubmittedError(ValueError):
    pass


class ReviewerCannotSelfSecondaryError(ValueError):
    pass


class PermissionDeniedError(ValueError):
    pass


class AdjudicationNotRequiredError(ValueError):
    pass


class AdjudicationReasonRequiredError(ValueError):
    pass


def start_review(db: Session, *, tenant_id: str, annotation_id: int) -> AnnotationReview:
    existing = (
        db.query(AnnotationReview)
        .filter(AnnotationReview.tenant_id == tenant_id, AnnotationReview.annotation_id == annotation_id)
        .first()
    )
    if existing is not None:
        return existing
    row = AnnotationReview(tenant_id=tenant_id, annotation_id=annotation_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _require_reviewer_role(actor_role: str) -> None:
    if actor_role not in ROLES_MAY_REVIEW:
        raise PermissionDeniedError(f"Role '{actor_role}' may not submit an annotation review.")


def submit_primary(
    db: Session, review: AnnotationReview, *, reviewer: str, actor_role: str, label: str,
    confidence: float | None = None, comments: str = "",
) -> AnnotationReview:
    _require_reviewer_role(actor_role)
    if review.primary_submitted_at is not None:
        raise ReviewAlreadySubmittedError("Primary review already submitted for this annotation.")
    review.primary_reviewer = reviewer
    review.primary_label = label
    review.primary_confidence = confidence
    review.primary_comments = comments
    review.primary_submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)

    record_enterprise_audit_event(
        db, action_type="annotation_reviewer_assigned", resource_type="annotation_review", resource_id=review.id,
        tenant_id=review.tenant_id, actor_email=reviewer, actor_role=actor_role,
        details={"annotation_id": review.annotation_id, "role": "primary"},
    )
    return review


def submit_secondary(
    db: Session, review: AnnotationReview, *, reviewer: str, actor_role: str, label: str,
    confidence: float | None = None, comments: str = "",
) -> AnnotationReview:
    """Blind by construction: never reads or exposes `primary_label` to the
    caller before recording the independent one."""
    _require_reviewer_role(actor_role)
    if review.secondary_submitted_at is not None:
        raise ReviewAlreadySubmittedError("Secondary review already submitted for this annotation.")
    if reviewer and reviewer == review.primary_reviewer:
        raise ReviewerCannotSelfSecondaryError(
            "The secondary reviewer must be a different person from the primary reviewer.",
        )
    review.secondary_reviewer = reviewer
    review.secondary_label = label
    review.secondary_confidence = confidence
    review.secondary_comments = comments
    review.secondary_submitted_at = datetime.now(timezone.utc)

    if review.primary_submitted_at is not None:
        review.agreement = review.primary_label == label

    db.commit()
    db.refresh(review)

    record_enterprise_audit_event(
        db, action_type="annotation_reviewer_assigned", resource_type="annotation_review", resource_id=review.id,
        tenant_id=review.tenant_id, actor_email=reviewer, actor_role=actor_role,
        details={"annotation_id": review.annotation_id, "role": "secondary", "agreement": review.agreement},
    )
    return review


def adjudicate(
    db: Session, review: AnnotationReview, *, adjudicator: str, actor_role: str, resolution: str, reason: str,
) -> AnnotationReview:
    """Section 5/14 — Clinical Reviewer/Administrator only. Requires a real
    disagreement (agreement is False) — never used to short-circuit a
    review that never happened."""
    if actor_role not in ROLES_MAY_FINALIZE_GROUND_TRUTH:
        raise PermissionDeniedError(f"Role '{actor_role}' may not adjudicate an annotation review.")
    if review.agreement is not False:
        raise AdjudicationNotRequiredError(
            "Adjudication is only valid when primary and secondary reviewers disagreed.",
        )
    if not reason.strip():
        raise AdjudicationReasonRequiredError("An adjudication reason is required.")

    review.adjudicator = adjudicator
    review.resolution = resolution
    review.adjudication_reason = reason
    review.disagreement_reason = review.disagreement_reason or reason
    review.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)

    record_enterprise_audit_event(
        db, action_type="annotation_adjudicated", resource_type="annotation_review", resource_id=review.id,
        tenant_id=review.tenant_id, actor_email=adjudicator, actor_role=actor_role,
        details={"annotation_id": review.annotation_id, "resolution": resolution},
    )
    return review


def record_disagreement_reason(db: Session, review: AnnotationReview, *, reason: str) -> AnnotationReview:
    review.disagreement_reason = reason
    db.commit()
    db.refresh(review)
    return review


def get_review(db: Session, *, tenant_id: str, annotation_id: int) -> AnnotationReview | None:
    return (
        db.query(AnnotationReview)
        .filter(AnnotationReview.tenant_id == tenant_id, AnnotationReview.annotation_id == annotation_id)
        .first()
    )
