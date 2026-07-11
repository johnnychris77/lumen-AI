"""Project Sage, Section 5: Adaptive Learning Plans.

A plan is only "assigned" in the sense a technician can see it once an
authorized educator/supervisor/manager has approved it (`approved_by` set) --
`create_learning_plan` never sets `approved_by` itself. Editing or rejecting
a *high-confidence* recommendation requires `override_reason` (Section 12);
this is enforced here, not just documented.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.sage_education import PLAN_STATUS_CANCELLED, SCOPE_INDIVIDUAL, SageLearningPlan


class OverrideReasonRequiredError(ValueError):
    pass


def create_learning_plan(
    db: Session, tenant_id: str, *, learner_or_group: str, created_by: str,
    knowledge_gap_id: int | None = None, scope_type: str = SCOPE_INDIVIDUAL,
    identified_need: str = "", supporting_evidence: dict | None = None, learning_objective: str = "",
    instrument_family: str = "", anatomy_zone: str = "", finding_category: str = "",
    education_content: str = "", microlearning_module_id: int | None = None, practice_activity: str = "",
    return_demonstration_required: bool = False, evaluator: str = "", due_date: datetime | None = None,
    confidence: str = "moderate",
) -> SageLearningPlan:
    row = SageLearningPlan(
        tenant_id=tenant_id, knowledge_gap_id=knowledge_gap_id, learner_or_group=learner_or_group,
        scope_type=scope_type, identified_need=identified_need,
        supporting_evidence_json=json.dumps(supporting_evidence or {}), learning_objective=learning_objective,
        instrument_family=instrument_family, anatomy_zone=anatomy_zone, finding_category=finding_category,
        education_content=education_content, microlearning_module_id=microlearning_module_id,
        practice_activity=practice_activity, return_demonstration_required=return_demonstration_required,
        evaluator=evaluator, due_date=due_date, confidence=confidence, created_by=created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def approve_learning_plan(db: Session, tenant_id: str, plan_id: int, *, approved_by: str) -> SageLearningPlan | None:
    """Assignment requires this call -- a plan is not visible to its
    learner via `list_plans_for_learner` until `approved_by` is set."""
    row = db.query(SageLearningPlan).filter(SageLearningPlan.id == plan_id, SageLearningPlan.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.approved_by = approved_by
    row.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def reject_or_edit_learning_plan(
    db: Session, tenant_id: str, plan_id: int, *, acted_by: str, action: str,
    override_reason: str = "", edits: dict | None = None,
) -> SageLearningPlan | None:
    """`action` is 'reject' or 'edit'. If the plan's own confidence is
    'high', `override_reason` is required -- raises otherwise."""
    row = db.query(SageLearningPlan).filter(SageLearningPlan.id == plan_id, SageLearningPlan.tenant_id == tenant_id).first()
    if row is None:
        return None
    if row.confidence == "high" and not override_reason.strip():
        raise OverrideReasonRequiredError(
            "override_reason is required to reject or edit a high-confidence Sage recommendation"
        )
    row.override_reason = override_reason
    if action == "reject":
        row.completion_status = PLAN_STATUS_CANCELLED
    elif action == "edit" and edits:
        for field in ("learning_objective", "practice_activity", "instrument_family", "anatomy_zone", "evaluator"):
            if field in edits:
                setattr(row, field, edits[field])
    db.commit()
    db.refresh(row)
    return row


def mark_completed(db: Session, tenant_id: str, plan_id: int) -> SageLearningPlan | None:
    row = db.query(SageLearningPlan).filter(SageLearningPlan.id == plan_id, SageLearningPlan.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.completion_status = "completed"
    row.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: SageLearningPlan) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "tenant_id": row.tenant_id,
        "knowledge_gap_id": row.knowledge_gap_id,
        "learner_or_group": row.learner_or_group,
        "scope_type": row.scope_type,
        "identified_need": row.identified_need,
        "supporting_evidence": json.loads(row.supporting_evidence_json or "{}"),
        "learning_objective": row.learning_objective,
        "instrument_family": row.instrument_family,
        "anatomy_zone": row.anatomy_zone,
        "finding_category": row.finding_category,
        "education_content": row.education_content,
        "microlearning_module_id": row.microlearning_module_id,
        "practice_activity": row.practice_activity,
        "return_demonstration_required": row.return_demonstration_required,
        "return_demonstration_validated": row.return_demonstration_validated,
        "evaluator": row.evaluator,
        "due_date": row.due_date.isoformat() if row.due_date else None,
        "completion_status": row.completion_status,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "effectiveness_assessment_id": row.effectiveness_assessment_id,
        "confidence": row.confidence,
        "approved_by": row.approved_by,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
        "override_reason": row.override_reason,
        "created_by": row.created_by,
        "human_review_required": row.human_review_required,
        "agent_version": row.agent_version,
    }


def get_plan(db: Session, tenant_id: str, plan_id: int) -> dict | None:
    row = db.query(SageLearningPlan).filter(SageLearningPlan.id == plan_id, SageLearningPlan.tenant_id == tenant_id).first()
    return to_dict(row) if row else None


def list_plans(db: Session, tenant_id: str, *, learner_or_group: str = "", completion_status: str = "") -> list[dict]:
    q = db.query(SageLearningPlan).filter(SageLearningPlan.tenant_id == tenant_id)
    if learner_or_group:
        q = q.filter(SageLearningPlan.learner_or_group == learner_or_group)
    if completion_status:
        q = q.filter(SageLearningPlan.completion_status == completion_status)
    return [to_dict(r) for r in q.order_by(SageLearningPlan.created_at.desc()).all()]


def list_plans_for_learner(db: Session, tenant_id: str, learner: str) -> list[dict]:
    """Section 11 -- only this learner's own APPROVED (assigned) plans,
    never a peer's."""
    rows = (
        db.query(SageLearningPlan)
        .filter(
            SageLearningPlan.tenant_id == tenant_id, SageLearningPlan.learner_or_group == learner,
            SageLearningPlan.approved_by != "",
        )
        .order_by(SageLearningPlan.created_at.desc())
        .all()
    )
    return [to_dict(r) for r in rows]
