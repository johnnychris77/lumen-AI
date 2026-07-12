"""Project Maestro, Section 6: Strategy Timeline.

A pure query over `MaestroRecommendation` -- there is no separate timeline
table. Recommendations are grouped by `timeline_horizon` and, within each
horizon, by `status`, so leadership can see what's due today versus this
quarter, and what's still pending versus already actioned.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.maestro_orchestration import TIMELINE_HORIZONS, MaestroRecommendation
from app.services.maestro_recommendation_engine_service import to_dict


def strategy_timeline(db: Session, tenant_id: str) -> dict:
    rows = (
        db.query(MaestroRecommendation)
        .filter(MaestroRecommendation.tenant_id == tenant_id)
        .order_by(MaestroRecommendation.created_at.desc())
        .all()
    )

    by_horizon: dict[str, list[dict]] = {horizon: [] for horizon in TIMELINE_HORIZONS}
    for row in rows:
        by_horizon.setdefault(row.timeline_horizon, []).append(to_dict(row))

    return {
        "horizons": by_horizon,
        "total_recommendations": len(rows),
        "human_review_required": True,
    }


def move_horizon(db: Session, tenant_id: str, recommendation_id: int, timeline_horizon: str) -> MaestroRecommendation | None:
    if timeline_horizon not in TIMELINE_HORIZONS:
        raise ValueError(f"Unknown timeline horizon: {timeline_horizon}")
    row = (
        db.query(MaestroRecommendation)
        .filter(MaestroRecommendation.tenant_id == tenant_id, MaestroRecommendation.id == recommendation_id)
        .first()
    )
    if row is None:
        return None
    row.timeline_horizon = timeline_horizon
    db.commit()
    db.refresh(row)
    return row
