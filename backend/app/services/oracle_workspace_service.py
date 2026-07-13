"""Project Oracle, Section 9: Research Workspace.

Aggregates counts and a combined recent-activity feed across every Oracle
record type for one tenant -- a pure read composition over the other
Oracle services and tables, never a separately persisted summary.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.oracle_discovery import (
    OracleDigitalTwinInsight,
    OracleHypothesis,
    OracleKnowledgeSuggestion,
    OracleModelObservation,
    OracleStageTransition,
    OracleTrendObservation,
)


def workspace_summary(db: Session, tenant_id: str, *, activity_limit: int = 20) -> dict:
    hyp_q = db.query(OracleHypothesis).filter(OracleHypothesis.tenant_id == tenant_id)
    trend_q = db.query(OracleTrendObservation).filter(OracleTrendObservation.tenant_id == tenant_id)
    twin_q = db.query(OracleDigitalTwinInsight).filter(OracleDigitalTwinInsight.tenant_id == tenant_id)
    model_q = db.query(OracleModelObservation).filter(OracleModelObservation.tenant_id == tenant_id)
    suggestion_q = db.query(OracleKnowledgeSuggestion).filter(OracleKnowledgeSuggestion.tenant_id == tenant_id)

    hypotheses = hyp_q.all()
    trends = trend_q.all()
    twins = twin_q.all()
    models_ = model_q.all()
    suggestions = suggestion_q.all()

    by_stage: dict[str, int] = {}
    for h in hypotheses:
        by_stage[h.current_stage] = by_stage.get(h.current_stage, 0) + 1

    by_direction: dict[str, int] = {}
    for t in trends:
        by_direction[t.direction] = by_direction.get(t.direction, 0) + 1

    by_source_service: dict[str, int] = {}
    for i in twins:
        by_source_service[i.source_service] = by_source_service.get(i.source_service, 0) + 1

    by_suggestion_status: dict[str, int] = {}
    for s in suggestions:
        by_suggestion_status[s.status] = by_suggestion_status.get(s.status, 0) + 1

    activity: list[dict] = []
    transitions = (
        db.query(OracleStageTransition)
        .filter(OracleStageTransition.tenant_id == tenant_id)
        .order_by(OracleStageTransition.created_at.desc())
        .limit(activity_limit)
        .all()
    )
    for tr in transitions:
        activity.append({
            "type": "stage_transition", "created_at": tr.created_at.isoformat() if tr.created_at else None,
            "hypothesis_id": tr.hypothesis_id, "from_stage": tr.from_stage, "to_stage": tr.to_stage,
            "changed_by": tr.changed_by, "reason": tr.reason,
        })
    for t in trends:
        activity.append({
            "type": "trend_observation", "created_at": t.created_at.isoformat() if t.created_at else None,
            "id": t.id, "metric_name": t.metric_name, "direction": t.direction,
        })
    for i in twins:
        activity.append({
            "type": "digital_twin_insight", "created_at": i.created_at.isoformat() if i.created_at else None,
            "id": i.id, "source_service": i.source_service, "insight_summary": i.insight_summary,
        })
    for m in models_:
        activity.append({
            "type": "model_observation", "created_at": m.created_at.isoformat() if m.created_at else None,
            "id": m.id, "observation_type": m.observation_type, "summary": m.summary,
        })
    activity.sort(key=lambda row: row["created_at"] or "", reverse=True)

    return {
        "hypotheses": {"total": len(hypotheses), "by_stage": by_stage},
        "trend_observations": {"total": len(trends), "by_direction": by_direction},
        "digital_twin_insights": {"total": len(twins), "by_source_service": by_source_service},
        "model_observations": {
            "total": len(models_), "unreviewed_count": sum(1 for m in models_ if not m.reviewed),
        },
        "knowledge_suggestions": {"total": len(suggestions), "by_status": by_suggestion_status},
        "recent_activity": activity[:activity_limit],
    }
