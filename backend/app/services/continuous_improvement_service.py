"""v1.5 — Continuous Improvement Tracker (Deliverable 11)."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.continuous_improvement import ContinuousImprovementInitiative


def create_initiative(
    db: Session, *, tenant_id: str, initiative: str, owner: str = "",
    target_date: date | None = None, expected_impact: str = "",
) -> ContinuousImprovementInitiative:
    row = ContinuousImprovementInitiative(
        tenant_id=tenant_id,
        initiative=initiative,
        owner=owner,
        target_date=target_date,
        expected_impact=expected_impact,
    )
    db.add(row)
    return row


def list_initiatives(db: Session, tenant_id: str) -> list[ContinuousImprovementInitiative]:
    return (
        db.query(ContinuousImprovementInitiative)
        .filter(ContinuousImprovementInitiative.tenant_id == tenant_id)
        .order_by(ContinuousImprovementInitiative.created_at.desc())
        .all()
    )


def update_initiative(
    db: Session, *, initiative_id: int, tenant_id: str,
    status: str | None = None, actual_impact: str | None = None,
) -> ContinuousImprovementInitiative | None:
    row = (
        db.query(ContinuousImprovementInitiative)
        .filter(
            ContinuousImprovementInitiative.id == initiative_id,
            ContinuousImprovementInitiative.tenant_id == tenant_id,
        )
        .first()
    )
    if row is None:
        return None
    if status is not None:
        row.status = status
    if actual_impact is not None:
        row.actual_impact = actual_impact
    return row
