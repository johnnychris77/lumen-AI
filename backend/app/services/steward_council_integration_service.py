"""Project Steward, Section 15: Council integration.

Council provides the approved recommendation, dissent, conditions,
required evidence, and approving authority; Steward returns
implementation status, completion evidence, measured outcome,
unintended consequences, and a closure recommendation. Council may
reopen a case when implementation fails or new evidence changes the
decision -- Steward never reopens a Council Case itself, it only
recommends it via `CLOSURE_REOPEN_SOURCE_CASE`.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.governed_action import GovernedAction, SOURCE_COUNCIL_CASE
from app.services import (
    steward_action_service,
    steward_unintended_consequence_service,
    steward_verification_service,
)
from app.services.council_human_decision_service import decisions_for_case
from app.services.council_orchestration_service import get_case


def create_action_from_council_decision(
    db: Session, tenant_id: str, council_case_id: int, *, category: str, action_type: str, action_title: str,
    action_description: str = "", owner: str = "", accountable_leader: str = "", facility_id: str = "",
    priority: str = "medium", due_date=None,
) -> GovernedAction:
    case = get_case(db, tenant_id, council_case_id)
    if case is None:
        raise ValueError("Council Case not found")
    decisions = decisions_for_case(db, tenant_id, council_case_id)
    if not decisions:
        raise ValueError(
            "This Council Case has no recorded human decision yet -- Steward cannot begin implementation "
            "of an unapproved recommendation."
        )
    latest_decision = decisions[-1]

    return steward_action_service.create_action(
        db, tenant_id, source_type=SOURCE_COUNCIL_CASE, source_id=str(council_case_id),
        source_decision=latest_decision["decision"], approved_by=latest_decision["approver"],
        approval_timestamp=case.created_at, action_title=action_title, action_description=action_description,
        category=category, action_type=action_type, owner=owner, accountable_leader=accountable_leader,
        facility_id=facility_id or case.facility_id, priority=priority, risk_level=case.risk_level or "medium",
        due_date=due_date, changed_by=latest_decision["approver"], changed_by_role=latest_decision["approver_role"],
    )


def council_status_return(db: Session, tenant_id: str, action_id: int) -> dict:
    """Section 15: what Steward reports back to Council for a
    Council-sourced action."""
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    unreviewed = [c for c in steward_unintended_consequence_service.list_consequences(db, tenant_id, action_id) if not c["reviewed"]]
    return {
        "governed_action_id": action.id,
        "council_case_id": action.source_id if action.source_type == SOURCE_COUNCIL_CASE else None,
        "implementation_status": action.status,
        "completion_evidence_sufficient": steward_verification_service.has_sufficient_evidence(db, tenant_id, action_id),
        "measured_outcome": action.benefits_realization or None,
        "unintended_consequences": unreviewed,
        "closure_recommendation": action.closure_decision or None,
        "recommend_reopen": bool(unreviewed) or action.benefits_realization == "worsened",
    }
