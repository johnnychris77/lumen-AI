"""Annotation Database — Section 6: Ground Truth Management.

Ground Truth becomes `ACTIVE` only after Primary Review + independent
Secondary Review with agreement, or Clinical Adjudication resolving a
disagreement. AI predictions never take this path — there is no code
path here that reads `Annotation.model_version` (AI-assisted) as
sufficient justification on its own; only a real `AnnotationReview`
record can promote an annotation to Ground Truth.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.annotation_database import (
    GROUND_TRUTH_ACTIVE,
    ROLES_MAY_FINALIZE_GROUND_TRUTH,
    Annotation,
    AnnotationReview,
)
from app.services.enterprise_audit_service import record_enterprise_audit_event


class GroundTruthNotEligibleError(ValueError):
    pass


class PermissionDeniedError(ValueError):
    pass


def is_eligible_for_ground_truth(review: AnnotationReview | None) -> tuple[bool, str]:
    if review is None:
        return False, "No review record exists for this annotation."
    if review.agreement is True:
        return True, "Primary and independent secondary reviewers agreed."
    if review.resolved_at is not None and review.resolution:
        return True, "Resolved via clinical adjudication."
    return False, "Independent review agreement or clinical adjudication has not yet occurred."


def promote_to_ground_truth(
    db: Session, annotation: Annotation, review: AnnotationReview, *, actor: str, actor_role: str,
) -> Annotation:
    if actor_role not in ROLES_MAY_FINALIZE_GROUND_TRUTH:
        raise PermissionDeniedError(f"Role '{actor_role}' may not finalize Ground Truth.")

    eligible, reason = is_eligible_for_ground_truth(review)
    if not eligible:
        raise GroundTruthNotEligibleError(reason)

    annotation.ground_truth_status = GROUND_TRUTH_ACTIVE
    annotation.ground_truth_version += 1
    annotation.review_status = "APPROVED"
    annotation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(annotation)

    record_enterprise_audit_event(
        db, action_type="annotation_ground_truth_promoted", resource_type="annotation",
        resource_id=annotation.ann_id, tenant_id=annotation.tenant_id, actor_email=actor, actor_role=actor_role,
        details={"ground_truth_version": annotation.ground_truth_version, "reason": reason},
    )
    return annotation
