"""Project Steward, Section 24: Closure Governance.

Closure criteria: required work completed, evidence verified, outcome
reviewed, residual risk documented (high-risk only), unintended
consequences reviewed, owner comments recorded, and an appropriate
approver signs off (enforced by `steward_action_service.transition_status`'s
own tier check for the CLOSED status).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.governed_action import CLOSURE_OUTCOMES, GovernedAction, STATUS_CLOSED
from app.services import (
    steward_action_service,
    steward_residual_risk_service,
    steward_unintended_consequence_service,
    steward_verification_service,
)


def close_action(
    db: Session, tenant_id: str, action_id: int, *, closure_decision: str, closed_by: str, closed_by_role: str,
    owner_comments: str, actor_facility_id: str = "",
) -> GovernedAction:
    if closure_decision not in CLOSURE_OUTCOMES:
        raise ValueError(f"Unknown closure decision: {closure_decision}")
    if not owner_comments.strip():
        raise ValueError("Closure requires owner comments to be recorded.")

    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")

    is_high_risk = action.risk_level in ("high", "critical")
    if is_high_risk:
        if not steward_verification_service.has_sufficient_evidence(db, tenant_id, action_id):
            raise ValueError("A high-risk action cannot be closed until its completion evidence is verified sufficient.")
        if not steward_residual_risk_service.has_reviewed_residual_risk(db, tenant_id, action_id):
            raise ValueError("A high-risk action cannot be closed without a documented residual-risk review.")

    unreviewed = [c for c in steward_unintended_consequence_service.list_consequences(db, tenant_id, action_id) if not c["reviewed"]]
    if unreviewed:
        raise ValueError("This action has unreviewed unintended consequences and cannot be closed yet.")

    action = steward_action_service.transition_status(
        db, tenant_id, action_id, new_status=STATUS_CLOSED, changed_by=closed_by, changed_by_role=closed_by_role,
        reason=owner_comments, actor_facility_id=actor_facility_id,
    )
    action.closure_decision = closure_decision
    db.commit()
    db.refresh(action)
    return action
