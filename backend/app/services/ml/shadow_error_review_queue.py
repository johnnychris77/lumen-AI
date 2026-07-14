"""Shadow §6 — Error Review Queue.

Auto-routes every disagreement (any comparison_category other than
"agreement") to a persisted, stateful review record — distinct from
``app.services.ml.pilot_validation.safety_review_queue()``, which is a
computed, safety-only view with no reviewer workflow. Every disagreement
becomes a review item here, not just safety-flagged ones.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.shadow_prediction import ShadowPrediction
from app.models.shadow_validation import ShadowErrorReviewItem

_AGREEMENT_CATEGORIES = {"agreement"}


def route_if_disagreement(db: Session, shadow_row: ShadowPrediction) -> ShadowErrorReviewItem | None:
    """Create a queue item for ``shadow_row`` if it disagreed with the
    human ground truth. A no-op (returns None) for agreements, for
    not-yet-reconciled rows, and for rows already queued."""
    if not shadow_row.comparison_category or shadow_row.comparison_category in _AGREEMENT_CATEGORIES:
        return None
    existing = (
        db.query(ShadowErrorReviewItem)
        .filter(ShadowErrorReviewItem.shadow_prediction_id == shadow_row.id)
        .first()
    )
    if existing is not None:
        return existing

    item = ShadowErrorReviewItem(
        tenant_id=shadow_row.tenant_id,
        shadow_prediction_id=shadow_row.id,
        inspection_id=shadow_row.inspection_id,
        model_id=shadow_row.model_id,
        human_decision=shadow_row.supervisor_final_label,
        ai_prediction=shadow_row.predicted_label,
        ai_confidence=_as_float(shadow_row.predicted_confidence),
        comparison_category=shadow_row.comparison_category,
        status="open",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _as_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def resolve_item(
    db: Session, item: ShadowErrorReviewItem, *, resolved_by: str,
    reviewer_comments: str = "", failure_classification: str = "",
) -> ShadowErrorReviewItem:
    item.status = "resolved"
    item.resolved_by = resolved_by
    item.resolved_at = datetime.now(timezone.utc)
    item.reviewer_comments = reviewer_comments
    if failure_classification:
        item.failure_classification = failure_classification
    db.commit()
    db.refresh(item)
    return item


def list_queue(db: Session, tenant_id: str, *, status: str | None = None) -> list[ShadowErrorReviewItem]:
    q = db.query(ShadowErrorReviewItem).filter(ShadowErrorReviewItem.tenant_id == tenant_id)
    if status:
        q = q.filter(ShadowErrorReviewItem.status == status)
    return q.order_by(ShadowErrorReviewItem.id.desc()).all()
