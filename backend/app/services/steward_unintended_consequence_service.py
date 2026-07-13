"""Project Steward, Section 11: Unintended Consequence Monitoring.

Flagging a consequence never edits or removes the action's existing
implementation history (audit trail, verifications, rollout results) --
it only adds a new row and, if the action isn't already in a terminal
state, moves its status to AT_RISK so it surfaces on every workspace/board
view until reviewed.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.governed_action import GovernedActionUnintendedConsequence, STATUS_AT_RISK, TERMINAL_STATUSES
from app.services import steward_action_service

CONSEQUENCE_TYPES = [
    "new_workflow_bottleneck", "increased_inspection_time", "increased_supervisor_workload",
    "new_image_quality_problem", "increased_evidence_overrides", "reduced_throughput",
    "increased_repair_referrals", "user_confusion", "risk_displacement",
]


def to_dict(row: GovernedActionUnintendedConsequence) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "governed_action_id": row.governed_action_id,
        "consequence_type": row.consequence_type,
        "description": row.description,
        "supporting_evidence": row.supporting_evidence,
        "reviewed": row.reviewed,
        "review_notes": row.review_notes,
    }


def flag_consequence(
    db: Session, tenant_id: str, action_id: int, *, consequence_type: str, description: str = "",
    supporting_evidence: str = "", changed_by: str = "", changed_by_role: str = "",
) -> GovernedActionUnintendedConsequence:
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    row = GovernedActionUnintendedConsequence(
        tenant_id=tenant_id, governed_action_id=action_id, consequence_type=consequence_type,
        description=description, supporting_evidence=supporting_evidence,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    if action.status not in TERMINAL_STATUSES and action.status != STATUS_AT_RISK:
        steward_action_service.transition_status(
            db, tenant_id, action_id, new_status=STATUS_AT_RISK, changed_by=changed_by,
            changed_by_role=changed_by_role, reason=f"Unintended consequence flagged: {consequence_type}.",
        )
    return row


def review_consequence(
    db: Session, tenant_id: str, consequence_id: int, *, review_notes: str,
) -> GovernedActionUnintendedConsequence:
    row = db.query(GovernedActionUnintendedConsequence).filter(
        GovernedActionUnintendedConsequence.tenant_id == tenant_id, GovernedActionUnintendedConsequence.id == consequence_id,
    ).first()
    if row is None:
        raise ValueError("Unintended consequence record not found")
    row.reviewed = True
    row.review_notes = review_notes
    db.commit()
    db.refresh(row)
    return row


def list_consequences(db: Session, tenant_id: str, action_id: int) -> list[dict]:
    rows = (
        db.query(GovernedActionUnintendedConsequence)
        .filter(GovernedActionUnintendedConsequence.tenant_id == tenant_id, GovernedActionUnintendedConsequence.governed_action_id == action_id)
        .order_by(GovernedActionUnintendedConsequence.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]
