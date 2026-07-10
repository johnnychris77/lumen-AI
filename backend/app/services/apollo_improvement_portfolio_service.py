"""v4.7 — Project Apollo, Section 8: Continuous Improvement Portfolio.

Composes the pre-existing `ContinuousImprovementInitiative` table (now
extended with methodology/cost-savings/quality-improvement/risk-reduction/
executive-visibility columns) — no new table, no re-derivation of
`actual_impact` (still human-filled only).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.continuous_improvement import METHODOLOGIES, ContinuousImprovementInitiative
from app.services import continuous_improvement_service


def _to_dict(row: ContinuousImprovementInitiative) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "tenant_id": row.tenant_id,
        "initiative": row.initiative,
        "owner": row.owner,
        "target_date": row.target_date.isoformat() if row.target_date else None,
        "status": row.status,
        "expected_impact": row.expected_impact,
        "actual_impact": row.actual_impact,
        "methodology": row.methodology,
        "cost_savings_usd": row.cost_savings_usd,
        "quality_improvement_metric": row.quality_improvement_metric,
        "risk_reduction_metric": row.risk_reduction_metric,
        "executive_visible": row.executive_visible,
    }


def create_project(
    db: Session, *, tenant_id: str, initiative: str, owner: str = "", target_date: date | None = None,
    expected_impact: str = "", methodology: str = "", cost_savings_usd: float | None = None,
    quality_improvement_metric: str = "", risk_reduction_metric: str = "", executive_visible: bool = False,
) -> dict:
    row = continuous_improvement_service.create_initiative(
        db, tenant_id=tenant_id, initiative=initiative, owner=owner, target_date=target_date,
        expected_impact=expected_impact, methodology=methodology, cost_savings_usd=cost_savings_usd,
        quality_improvement_metric=quality_improvement_metric, risk_reduction_metric=risk_reduction_metric,
        executive_visible=executive_visible,
    )
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def list_projects(db: Session, tenant_id: str) -> list[dict]:
    return [_to_dict(r) for r in continuous_improvement_service.list_initiatives(db, tenant_id)]


def update_project(db: Session, *, tenant_id: str, initiative_id: int, **fields) -> dict | None:
    row = continuous_improvement_service.update_initiative(db, initiative_id=initiative_id, tenant_id=tenant_id, **fields)
    if row is None:
        return None
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def portfolio_summary(db: Session, tenant_id: str) -> dict:
    """PI/Lean/Six Sigma/Kaizen rollup: counts by methodology/status, total
    (human-entered) cost savings, and the executive-visible subset."""
    rows = continuous_improvement_service.list_initiatives(db, tenant_id)
    by_methodology: dict[str, int] = {m: 0 for m in METHODOLOGIES}
    by_status: dict[str, int] = {}
    total_cost_savings = 0.0
    executive_visible_projects = []
    for r in rows:
        if r.methodology:
            by_methodology[r.methodology] = by_methodology.get(r.methodology, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        if r.cost_savings_usd:
            total_cost_savings += r.cost_savings_usd
        if r.executive_visible:
            executive_visible_projects.append(_to_dict(r))

    return {
        "total_projects": len(rows),
        "by_methodology": by_methodology,
        "by_status": by_status,
        "total_cost_savings_usd": round(total_cost_savings, 2) if total_cost_savings else 0.0,
        "executive_visible_projects": executive_visible_projects,
        "completion_rate_pct": (
            round(100 * by_status.get("completed", 0) / len(rows), 1) if rows else None
        ),
        "human_review_required": True,
    }
