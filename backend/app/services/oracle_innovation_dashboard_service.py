"""Project Oracle, Section 14: Executive Innovation Dashboard.

A portfolio-level rollup across every hypothesis a tenant has -- the
validation-pipeline funnel, promoted-to-production count, average
time-to-validation for promoted hypotheses, category distribution, and
top research owners by hypothesis count. Pure read composition; nothing
here is separately persisted.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.oracle_discovery import (
    DISCOVERY_CATEGORIES,
    OUTCOME_PROMOTED,
    STAGE_PRODUCTION_KNOWLEDGE,
    STAGE_REJECTED,
    VALIDATION_STAGES,
    OracleHypothesis,
    OracleStageTransition,
)


def _time_to_validation_days(db: Session, tenant_id: str, hypothesis_id: int) -> float | None:
    transitions = (
        db.query(OracleStageTransition)
        .filter(OracleStageTransition.tenant_id == tenant_id, OracleStageTransition.hypothesis_id == hypothesis_id)
        .order_by(OracleStageTransition.created_at.asc())
        .all()
    )
    if not transitions:
        return None
    first_at = transitions[0].created_at
    promoted_at = next((t.created_at for t in transitions if t.to_stage == STAGE_PRODUCTION_KNOWLEDGE), None)
    if first_at is None or promoted_at is None:
        return None
    return max(0.0, (promoted_at - first_at).total_seconds() / 86400)


def innovation_dashboard(db: Session, tenant_id: str) -> dict:
    hypotheses = db.query(OracleHypothesis).filter(OracleHypothesis.tenant_id == tenant_id).all()

    funnel = {s: 0 for s in VALIDATION_STAGES}
    funnel[STAGE_REJECTED] = 0
    category_distribution = {c: 0 for c in DISCOVERY_CATEGORIES}
    owner_counts: dict[str, int] = {}

    promoted_ids = []
    for h in hypotheses:
        funnel[h.current_stage] = funnel.get(h.current_stage, 0) + 1
        category_distribution[h.discovery_category] = category_distribution.get(h.discovery_category, 0) + 1
        if h.research_owner:
            owner_counts[h.research_owner] = owner_counts.get(h.research_owner, 0) + 1
        if h.outcome == OUTCOME_PROMOTED:
            promoted_ids.append(h.id)

    validation_days = [
        d for d in (_time_to_validation_days(db, tenant_id, hid) for hid in promoted_ids) if d is not None
    ]
    avg_time_to_validation_days = round(sum(validation_days) / len(validation_days), 1) if validation_days else None

    top_owners = sorted(owner_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]

    return {
        "total_hypotheses": len(hypotheses),
        "pipeline_funnel": funnel,
        "promoted_to_production_count": len(promoted_ids),
        "avg_time_to_validation_days": avg_time_to_validation_days,
        "category_distribution": category_distribution,
        "top_research_owners": [{"research_owner": owner, "hypothesis_count": count} for owner, count in top_owners],
        "human_review_required": True,
    }
