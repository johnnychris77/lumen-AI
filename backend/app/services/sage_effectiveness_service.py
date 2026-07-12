"""Project Sage, Section 9: Learning Effectiveness Engine.

Compares real before/after metrics for one learner across a completed
learning plan's before-window (plan creation) and after-window (plan
completion) -- inspection coverage (`Inspection.coverage_pct`), supervisor
correction rate (`SupervisorReview.agreement`), image quality proxy
(`Inspection.ai_confidence` -- this codebase does not separately measure
image quality, so AI confidence on image-based inspections is the closest
real signal), finding accuracy (`SupervisorReview.finding_correct`), anatomy
accuracy (`SupervisorReview.zone_correct`), and workflow compliance
(`SupervisorReview.image_view_correct` + `missing_zone_correct`). Never
claims causation -- only classifies the pattern the numbers show.
"""
from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy.orm import Session

from app.db import models
from app.models.sage_education import (
    EFFECTIVENESS_DECLINED,
    EFFECTIVENESS_IMPROVED,
    EFFECTIVENESS_INSUFFICIENT_EVIDENCE,
    EFFECTIVENESS_PARTIALLY_IMPROVED,
    EFFECTIVENESS_UNCHANGED,
    SageEffectivenessAssessment,
)
from app.models.supervisor_review import SupervisorReview

_CHANGE_THRESHOLD_PCT = 5.0

# metric_name -> True if higher is better
_METRIC_DIRECTION = {
    "avg_coverage_pct": True,
    "avg_ai_confidence_pct": True,
    "finding_accuracy_pct": True,
    "anatomy_accuracy_pct": True,
    "workflow_compliance_pct": True,
    "supervisor_correction_rate_pct": False,
}


def _window_metrics(db: Session, tenant_id: str, technician: str, start, end) -> dict:
    inspections = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id, models.Inspection.technician == technician,
            models.Inspection.created_at >= start, models.Inspection.created_at < end,
        )
        .all()
    )
    coverage = [i.coverage_pct for i in inspections if i.coverage_pct is not None]
    confidences = [i.ai_confidence for i in inspections if i.has_image and i.ai_confidence is not None]

    insp_ids = [i.id for i in inspections]
    reviews = (
        db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.inspection_id.in_(insp_ids)).all()
    ) if insp_ids else []

    metrics: dict[str, float | None] = {
        "avg_coverage_pct": round(sum(coverage) / len(coverage), 1) if coverage else None,
        "avg_ai_confidence_pct": round(100 * sum(confidences) / len(confidences), 1) if confidences else None,
        "supervisor_correction_rate_pct": (
            round(100 * sum(1 for r in reviews if r.agreement != "agree") / len(reviews), 1) if reviews else None
        ),
        "finding_accuracy_pct": (
            round(100 * sum(1 for r in reviews if r.finding_correct) / sum(1 for r in reviews if r.finding_correct is not None), 1)
            if any(r.finding_correct is not None for r in reviews) else None
        ),
        "anatomy_accuracy_pct": (
            round(100 * sum(1 for r in reviews if r.zone_correct) / sum(1 for r in reviews if r.zone_correct is not None), 1)
            if any(r.zone_correct is not None for r in reviews) else None
        ),
        "workflow_compliance_pct": (
            round(
                100 * sum(1 for r in reviews if r.image_view_correct and r.missing_zone_correct)
                / sum(1 for r in reviews if r.image_view_correct is not None and r.missing_zone_correct is not None), 1
            )
            if any(r.image_view_correct is not None and r.missing_zone_correct is not None for r in reviews) else None
        ),
        "sample_size": len(inspections),
    }
    return metrics


def classify_effectiveness(before: dict, after: dict) -> str:
    tracked = [m for m in _METRIC_DIRECTION if before.get(m) is not None and after.get(m) is not None]
    if not tracked:
        return EFFECTIVENESS_INSUFFICIENT_EVIDENCE

    improved = declined = 0
    for metric in tracked:
        delta = after[metric] - before[metric]
        higher_is_better = _METRIC_DIRECTION[metric]
        signed_delta = delta if higher_is_better else -delta
        if signed_delta >= _CHANGE_THRESHOLD_PCT:
            improved += 1
        elif signed_delta <= -_CHANGE_THRESHOLD_PCT:
            declined += 1

    if improved == len(tracked):
        return EFFECTIVENESS_IMPROVED
    if declined == len(tracked):
        return EFFECTIVENESS_DECLINED
    if improved > declined:
        return EFFECTIVENESS_PARTIALLY_IMPROVED
    if declined > improved:
        return EFFECTIVENESS_DECLINED
    return EFFECTIVENESS_UNCHANGED


def measure_learning_plan_effectiveness(
    db: Session, tenant_id: str, learning_plan, *, window_days: int = 30,
) -> SageEffectivenessAssessment:
    """`learning_plan` must be a completed `SageLearningPlan` row (has
    `completed_at`)."""
    technician = learning_plan.learner_or_group
    before_start = learning_plan.created_at - timedelta(days=window_days)
    before = _window_metrics(db, tenant_id, technician, before_start, learning_plan.created_at)

    after_end = (learning_plan.completed_at or learning_plan.created_at) + timedelta(days=window_days)
    after = _window_metrics(db, tenant_id, technician, learning_plan.completed_at or learning_plan.created_at, after_end)

    effectiveness = classify_effectiveness(before, after)
    if effectiveness == EFFECTIVENESS_INSUFFICIENT_EVIDENCE:
        narrative = (
            f"Insufficient inspection/review activity in the before or after window to assess whether "
            f"education for {technician} improved outcomes."
        )
    else:
        narrative = (
            f"Comparing the {window_days} days before and after this learning plan's completion, "
            f"the recorded metrics for {technician} are classified as '{effectiveness.replace('_', ' ')}'. "
            "This reflects an observed pattern, not a confirmed causal effect of the education itself."
        )

    row = SageEffectivenessAssessment(
        tenant_id=tenant_id, learning_plan_id=learning_plan.id, learner_or_group=technician,
        before_metrics_json=json.dumps(before), after_metrics_json=json.dumps(after),
        effectiveness=effectiveness, narrative=narrative,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: SageEffectivenessAssessment) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "learning_plan_id": row.learning_plan_id,
        "learner_or_group": row.learner_or_group,
        "before_metrics": json.loads(row.before_metrics_json or "{}"),
        "after_metrics": json.loads(row.after_metrics_json or "{}"),
        "effectiveness": row.effectiveness,
        "narrative": row.narrative,
        "human_review_required": row.human_review_required,
    }
