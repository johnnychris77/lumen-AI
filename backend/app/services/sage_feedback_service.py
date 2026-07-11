"""Project Sage, Section 12: Educator and Supervisor Workspace actions.

Logs every educator/supervisor action (review/approve/reject/edit/assign/
document observation/validate return demonstration/close competency item/
review effectiveness/add comment) as a `SageFeedback` row -- the audit
record Section 17 requires. `override_reason` is required by the caller
(enforced in `sage_learning_plan_service`) for reject/edit actions on a
high-confidence recommendation; this service just persists whatever reason
was supplied.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sage_education import SageFeedback

VALID_ACTIONS = (
    "review", "approve", "reject", "edit_objective", "assign", "document_observation",
    "validate_return_demonstration", "close_competency_item", "review_effectiveness", "add_comment",
)


def record_feedback(
    db: Session, tenant_id: str, *, action: str, submitted_by: str, submitted_role: str = "",
    learning_plan_id: int | None = None, knowledge_gap_id: int | None = None,
    comment: str = "", override_reason: str = "",
) -> SageFeedback:
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unknown Sage feedback action '{action}'")
    row = SageFeedback(
        tenant_id=tenant_id, learning_plan_id=learning_plan_id, knowledge_gap_id=knowledge_gap_id,
        action=action, comment=comment, override_reason=override_reason,
        submitted_by=submitted_by, submitted_role=submitted_role,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: SageFeedback) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "learning_plan_id": row.learning_plan_id,
        "knowledge_gap_id": row.knowledge_gap_id,
        "action": row.action,
        "comment": row.comment,
        "override_reason": row.override_reason,
        "submitted_by": row.submitted_by,
        "submitted_role": row.submitted_role,
    }


def feedback_for_plan(db: Session, tenant_id: str, learning_plan_id: int) -> list[dict]:
    rows = (
        db.query(SageFeedback)
        .filter(SageFeedback.tenant_id == tenant_id, SageFeedback.learning_plan_id == learning_plan_id)
        .order_by(SageFeedback.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]
