"""Project Steward, Section 20: Sentinel-X residual-risk integration.

Compares Sentinel-X's own already-persisted risk assessments for an
instrument before, during, and after a Governed Action's implementation,
rather than recomputing risk from scratch. Closure of a high-risk action
requires a reviewed residual-risk row to exist.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.governed_action import GovernedActionResidualRiskReview
from app.models.sentinelx_risk import SentinelXRiskAssessment
from app.services import steward_action_service


def to_dict(row: GovernedActionResidualRiskReview) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "governed_action_id": row.governed_action_id,
        "risk_before": row.risk_before,
        "risk_during": row.risk_during,
        "risk_after": row.risk_after,
        "reviewed_by": row.reviewed_by,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "notes": row.notes,
    }


def current_average_risk_for_instrument(db: Session, tenant_id: str, instrument_identity: str) -> float | None:
    rows = (
        db.query(SentinelXRiskAssessment)
        .filter(SentinelXRiskAssessment.tenant_id == tenant_id, SentinelXRiskAssessment.instrument_identity == instrument_identity)
        .all()
    )
    if not rows:
        return None
    return round(sum(r.risk_score for r in rows) / len(rows), 1)


def record_residual_risk_review(
    db: Session, tenant_id: str, action_id: int, *, risk_before: float | None = None,
    risk_during: float | None = None, risk_after: float | None = None, instrument_identity: str = "",
    reviewed_by: str = "", notes: str = "",
) -> GovernedActionResidualRiskReview:
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    if instrument_identity:
        current = current_average_risk_for_instrument(db, tenant_id, instrument_identity)
        risk_after = risk_after if risk_after is not None else current
    row = GovernedActionResidualRiskReview(
        tenant_id=tenant_id, governed_action_id=action_id, risk_before=risk_before, risk_during=risk_during,
        risk_after=risk_after, reviewed_by=reviewed_by,
        reviewed_at=datetime.now(timezone.utc) if reviewed_by else None, notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_residual_risk_reviews(db: Session, tenant_id: str, action_id: int) -> list[dict]:
    rows = (
        db.query(GovernedActionResidualRiskReview)
        .filter(GovernedActionResidualRiskReview.tenant_id == tenant_id, GovernedActionResidualRiskReview.governed_action_id == action_id)
        .order_by(GovernedActionResidualRiskReview.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]


def has_reviewed_residual_risk(db: Session, tenant_id: str, action_id: int) -> bool:
    """Section 20/24: closure requires a documented residual-risk review
    (both `risk_after` recorded and a human reviewer) for high-risk
    actions."""
    rows = list_residual_risk_reviews(db, tenant_id, action_id)
    return any(r["risk_after"] is not None and r["reviewed_by"] for r in rows)
