"""Project Steward, Section 10: Benefits Realization Engine.

Compares one expected metric against its actual measured value and
classifies the result. Never claims success without a real measured
`actual_value` -- missing data always classifies as `inconclusive`,
never `achieved`, avoiding unsupported causal claims.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.governed_action import (
    BENEFITS_ACHIEVED,
    BENEFITS_EXCEEDED,
    BENEFITS_INCONCLUSIVE,
    BENEFITS_NOT_ACHIEVED,
    BENEFITS_PARTIALLY_ACHIEVED,
    BENEFITS_WORSENED,
    GovernedActionOutcomeReview,
)
from app.services import steward_action_service


def to_dict(row: GovernedActionOutcomeReview) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "governed_action_id": row.governed_action_id,
        "metric_name": row.metric_name,
        "baseline_value": row.baseline_value,
        "expected_value": row.expected_value,
        "actual_value": row.actual_value,
        "classification": row.classification,
        "notes": row.notes,
    }


def _classify(baseline: float | None, expected: float | None, actual: float | None, higher_is_better: bool) -> str:
    if actual is None or expected is None:
        return BENEFITS_INCONCLUSIVE
    delta_from_expected = (actual - expected) if higher_is_better else (expected - actual)
    if delta_from_expected > 0:
        return BENEFITS_EXCEEDED
    if delta_from_expected == 0:
        return BENEFITS_ACHIEVED
    if baseline is None:
        return BENEFITS_NOT_ACHIEVED
    delta_from_baseline = (actual - baseline) if higher_is_better else (baseline - actual)
    if delta_from_baseline > 0:
        return BENEFITS_PARTIALLY_ACHIEVED
    if delta_from_baseline == 0:
        return BENEFITS_NOT_ACHIEVED
    return BENEFITS_WORSENED


def record_outcome_review(
    db: Session, tenant_id: str, action_id: int, *, metric_name: str, baseline_value: float | None = None,
    expected_value: float | None = None, actual_value: float | None = None, higher_is_better: bool = True,
    notes: str = "",
) -> GovernedActionOutcomeReview:
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    classification = _classify(baseline_value, expected_value, actual_value, higher_is_better)
    row = GovernedActionOutcomeReview(
        tenant_id=tenant_id, governed_action_id=action_id, metric_name=metric_name, baseline_value=baseline_value,
        expected_value=expected_value, actual_value=actual_value, classification=classification, notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # Roll the most recent, most conclusive classification up onto the
    # action itself so the workspace/board views don't need to re-derive it.
    action.benefits_realization = classification
    action.actual_outcomes = notes or action.actual_outcomes
    db.commit()
    return row


def list_outcome_reviews(db: Session, tenant_id: str, action_id: int) -> list[dict]:
    rows = (
        db.query(GovernedActionOutcomeReview)
        .filter(GovernedActionOutcomeReview.tenant_id == tenant_id, GovernedActionOutcomeReview.governed_action_id == action_id)
        .order_by(GovernedActionOutcomeReview.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]
