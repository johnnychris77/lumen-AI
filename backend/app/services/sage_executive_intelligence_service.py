"""Project Sage, Section 18: Executive Workforce Intelligence.

Aggregate-only analytics for authorized leadership -- every number here is a
count or rate grouped by domain/instrument-family/anatomy-zone, never a
per-individual ranking list. No technician name appears in this summary.
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from app.models.sage_education import (
    EFFECTIVENESS_IMPROVED,
    EFFECTIVENESS_PARTIALLY_IMPROVED,
    PLAN_STATUS_COMPLETED,
    PLAN_STATUS_OVERDUE,
    SageEffectivenessAssessment,
    SageKnowledgeGap,
    SageLearningPlan,
)


def executive_workforce_intelligence(db: Session, tenant_id: str) -> dict:
    plans = db.query(SageLearningPlan).filter(SageLearningPlan.tenant_id == tenant_id).all()
    gaps = db.query(SageKnowledgeGap).filter(SageKnowledgeGap.tenant_id == tenant_id).all()
    effectiveness_rows = db.query(SageEffectivenessAssessment).filter(SageEffectivenessAssessment.tenant_id == tenant_id).all()

    total_plans = len(plans)
    completed_plans = sum(1 for p in plans if p.completion_status == PLAN_STATUS_COMPLETED)
    overdue_plans = sum(1 for p in plans if p.completion_status == PLAN_STATUS_OVERDUE)
    learners_with_plans = {p.learner_or_group for p in plans}
    learners_with_completed = {p.learner_or_group for p in plans if p.completion_status == PLAN_STATUS_COMPLETED}

    high_priority_gaps = [g for g in gaps if g.confidence == "high"]
    anatomy_zone_counts = Counter(g.anatomy_zone for g in gaps if g.anatomy_zone)
    instrument_family_counts = Counter(g.instrument_family for g in gaps if g.instrument_family)

    effectiveness_counts = Counter(r.effectiveness for r in effectiveness_rows)
    improved_count = effectiveness_counts.get(EFFECTIVENESS_IMPROVED, 0) + effectiveness_counts.get(EFFECTIVENESS_PARTIALLY_IMPROVED, 0)

    return {
        "competency_completion_pct": round(100 * completed_plans / total_plans, 1) if total_plans else None,
        "education_coverage_pct": (
            round(100 * len(learners_with_completed) / len(learners_with_plans), 1) if learners_with_plans else None
        ),
        "high_priority_knowledge_gap_count": len(high_priority_gaps),
        "anatomy_zone_training_needs": dict(anatomy_zone_counts),
        "instrument_family_training_needs": dict(instrument_family_counts),
        "improvement_after_education_pct": (
            round(100 * improved_count / len(effectiveness_rows), 1) if effectiveness_rows else None
        ),
        "overdue_competency_count": overdue_plans,
        "learning_effectiveness_breakdown": dict(effectiveness_counts),
        "total_learning_plans": total_plans,
        "human_review_required": True,
        "note": "Aggregate counts only -- no individual technician is ranked or named in this summary.",
    }
