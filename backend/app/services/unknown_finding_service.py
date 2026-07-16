"""Section 13 — Unknown-Finding Learning Loop.

When the Lumen Decision Engine observes a signal outside its validated
taxonomy, it opens an `UnknownFindingReview` instead of guessing a category.
A supervisor classification here is a candidate-dataset annotation only —
it never itself modifies production code, taxonomy, or model behavior. The
workflow this module supports:

    unknown finding -> supervisor classification -> clinical/data review
    -> second expert validation -> candidate dataset -> sufficient examples
    -> retraining -> independent validation -> governed model promotion

Only the first three steps (open, classify, second review) are implemented
here; retraining/promotion already exist as `candidate_promotion.py` from
prior phases and are intentionally not duplicated.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.lumen_decision_engine import UnknownFindingReview


def open_unknown_finding(
    db: Session,
    *,
    inspection_id: int,
    tenant_id: str,
    instrument_family: str,
    anatomy_zone: str,
    model_output: dict[str, Any],
    model_confidence: float | None,
    baseline_similarity: float | None,
    evidence_limitations: list[str],
    model_version: str,
) -> UnknownFindingReview:
    review = UnknownFindingReview(
        inspection_id=inspection_id,
        tenant_id=tenant_id,
        instrument_family=instrument_family,
        anatomy_zone=anatomy_zone,
        model_output=json.dumps(model_output, default=str),
        model_confidence=model_confidence,
        baseline_similarity=baseline_similarity,
        evidence_limitations_json=json.dumps(evidence_limitations),
        model_version=model_version,
        status="pending_supervisor",
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def classify_finding(
    db: Session, review: UnknownFindingReview, *, actor: str, actor_role: str,
    classification: str, comments: str = "",
) -> UnknownFindingReview:
    """A supervisor's classification of an unknown finding. This updates only
    the review record — it never writes to the model, taxonomy, or any
    production inference path."""
    if actor_role not in {"admin", "spd_manager"}:
        raise PermissionError(f"Role '{actor_role}' may not classify an unknown finding.")
    review.supervisor_classification = classification
    review.supervisor_comments = comments
    review.supervisor_actor = actor
    review.status = "classified"
    db.commit()
    db.refresh(review)
    return review


def record_second_review(
    db: Session, review: UnknownFindingReview, *, adjudicated_label: str,
    dataset_eligible: bool, usage_rights: str = "",
) -> UnknownFindingReview:
    if review.status != "classified":
        raise ValueError("Second review requires a prior supervisor classification.")
    review.adjudicated_label = adjudicated_label
    review.dataset_eligible = dataset_eligible
    review.usage_rights = usage_rights
    review.second_review_status = "completed"
    review.status = "second_review"
    db.commit()
    db.refresh(review)
    return review


def list_reviews(db: Session, *, tenant_id: str, status: str | None = None) -> list[UnknownFindingReview]:
    query = db.query(UnknownFindingReview).filter(UnknownFindingReview.tenant_id == tenant_id)
    if status:
        query = query.filter(UnknownFindingReview.status == status)
    return query.order_by(UnknownFindingReview.created_at.desc()).all()


class NotEligibleForDatasetError(ValueError):
    pass


def promote_to_candidate_dataset(
    db: Session, review: UnknownFindingReview, *, dataset_version_id: int, retained_image_id: int,
    image_sha256: str, facility: str = "", operator: str = "",
    manufacturer: str = "", capture_device: str = "", image_resolution: str = "",
):
    """LCID Sprint 1 (Section 8) — the second, later half of the unknown-
    finding workflow: once a supervisor-classified, second-reviewed unknown
    finding is marked `dataset_eligible`, register it as a UNLABELED
    candidate dataset entry (never auto-approved, never auto-expanding the
    taxonomy — see `docs/decision-engine/UNKNOWN_FINDING_LEARNING_LOOP.md`
    and `docs/lcid/UNKNOWN_FINDING_GUIDE.md`).

    Requires the caller to supply the real stored image
    (`retained_image_id`/`image_sha256`) — this service never fabricates an
    image reference `UnknownFindingReview` does not itself store one.
    """
    if not review.dataset_eligible:
        raise NotEligibleForDatasetError(
            f"UnknownFindingReview {review.id} is not marked dataset_eligible.",
        )
    if review.second_review_status != "completed":
        raise NotEligibleForDatasetError(
            f"UnknownFindingReview {review.id} has not completed second review.",
        )

    from app.services.ml.dataset_registry import register_image

    return register_image(
        db,
        tenant_id=review.tenant_id,
        dataset_version_id=dataset_version_id,
        retained_image_id=retained_image_id,
        image_sha256=image_sha256,
        inspection_id=review.inspection_id,
        instrument_family=review.instrument_family,
        anatomy_zone=review.anatomy_zone,
        manufacturer=manufacturer,
        capture_device=capture_device,
        image_resolution=image_resolution,
        facility=facility,
        operator=operator,
        usage_rights=review.usage_rights,
        phi_verification="pending",
    )
