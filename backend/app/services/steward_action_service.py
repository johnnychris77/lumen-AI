"""Project Steward, Section 1 & 2: the Steward Action Orchestration Agent
and the Governed Action object -- core CRUD, validation, and the
role-authorized, fully-audited lifecycle state machine.

No Governed Action may begin without an approved source decision (a
non-empty `approved_by` + `approval_timestamp`); this is enforced once,
here, at creation -- every other Steward service composes on top of an
already-validated action.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.governed_action import (
    ACTION_STATUSES,
    ACTION_TYPES_BY_CATEGORY,
    DISCLAIMER,
    GovernedAction,
    GovernedActionAuditEvent,
    ROLE_AUTHORITY_TIER,
    STATUS_APPROVED,
    STATUS_CANCELLED,
    STATUS_CLOSED,
    STATUS_DRAFT,
    STATUS_READY_TO_START,
    TERMINAL_STATUSES,
    TIER_APPROVE_HIGH_RISK,
    TIER_APPROVE_STANDARD,
    TIER_CLOSE_HIGH_RISK,
    TIER_CLOSE_STANDARD,
    TIER_CROSS_FACILITY_AUTHORITY,
)

# Status transitions that gate irreversible authority (approving or
# closing/cancelling an action) require an elevated, tier-checked role.
# Every other transition (BLOCKED, AT_RISK, IN_PROGRESS, etc.) only needs
# a valid tenant role -- it is operational tracking, not re-authorization.
_GATED_TRANSITIONS = {STATUS_APPROVED, STATUS_CLOSED, STATUS_CANCELLED}


def _is_high_risk(action: GovernedAction) -> bool:
    return action.risk_level in {"high", "critical"}


def _required_tier(action: GovernedAction, new_status: str) -> int:
    if new_status == STATUS_APPROVED:
        return TIER_APPROVE_HIGH_RISK if _is_high_risk(action) else TIER_APPROVE_STANDARD
    if new_status in (STATUS_CLOSED, STATUS_CANCELLED):
        return TIER_CLOSE_HIGH_RISK if _is_high_risk(action) else TIER_CLOSE_STANDARD
    return 0


def to_dict(row: GovernedAction) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "tenant_id": row.tenant_id,
        "facility_id": row.facility_id,
        "source_type": row.source_type,
        "source_id": row.source_id,
        "source_decision": row.source_decision,
        "approved_by": row.approved_by,
        "approval_timestamp": row.approval_timestamp.isoformat() if row.approval_timestamp else None,
        "action_title": row.action_title,
        "action_description": row.action_description,
        "category": row.category,
        "action_type": row.action_type,
        "owner": row.owner,
        "accountable_leader": row.accountable_leader,
        "stakeholders": json.loads(row.stakeholders_json or "[]"),
        "priority": row.priority,
        "risk_level": row.risk_level,
        "dependencies": json.loads(row.dependencies_json or "[]"),
        "milestones": json.loads(row.milestones_json or "[]"),
        "due_date": row.due_date.isoformat() if row.due_date else None,
        "status": row.status,
        "evidence_requirements": json.loads(row.evidence_requirements_json or "[]"),
        "expected_outcomes": row.expected_outcomes,
        "success_metrics": json.loads(row.success_metrics_json or "[]"),
        "actual_outcomes": row.actual_outcomes,
        "benefits_realization": row.benefits_realization,
        "unintended_consequences": json.loads(row.unintended_consequences_json or "[]"),
        "change_readiness": row.change_readiness,
        "closure_decision": row.closure_decision,
        "closure_approver": row.closure_approver,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "human_review_required": row.human_review_required,
        "agent_version": row.agent_version,
        "disclaimer": row.disclaimer,
    }


def _audit_to_dict(row: GovernedActionAuditEvent) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "governed_action_id": row.governed_action_id,
        "from_status": row.from_status,
        "to_status": row.to_status,
        "changed_by": row.changed_by,
        "changed_by_role": row.changed_by_role,
        "reason": row.reason,
    }


def _record_audit_event(
    db: Session, tenant_id: str, action_id: int, *, from_status: str, to_status: str,
    changed_by: str, changed_by_role: str, reason: str = "",
) -> None:
    db.add(GovernedActionAuditEvent(
        tenant_id=tenant_id, governed_action_id=action_id, from_status=from_status, to_status=to_status,
        changed_by=changed_by, changed_by_role=changed_by_role, reason=reason,
    ))


def create_action(
    db: Session, tenant_id: str, *, source_type: str, source_id: str, source_decision: str,
    approved_by: str, approval_timestamp: datetime | None, action_title: str, action_description: str = "",
    category: str, action_type: str, owner: str = "", accountable_leader: str = "", facility_id: str = "",
    priority: str = "medium", risk_level: str = "medium", stakeholders: list[str] | None = None,
    dependencies: list[dict] | None = None, due_date: datetime | None = None,
    evidence_requirements: list[str] | None = None, expected_outcomes: str = "",
    success_metrics: list[dict] | None = None, changed_by: str = "", changed_by_role: str = "",
) -> GovernedAction:
    """Section 1: no action may begin without an approved source decision."""
    if not source_decision.strip() or not approved_by.strip() or approval_timestamp is None:
        raise ValueError(
            "Steward cannot create a Governed Action from an unapproved recommendation -- "
            "source_decision, approved_by, and approval_timestamp are all required."
        )
    if category not in ACTION_TYPES_BY_CATEGORY:
        raise ValueError(f"Unknown action category: {category}")
    if action_type not in ACTION_TYPES_BY_CATEGORY[category]:
        raise ValueError(f"Action type '{action_type}' is not valid for category '{category}'")

    row = GovernedAction(
        tenant_id=tenant_id, facility_id=facility_id, source_type=source_type, source_id=str(source_id),
        source_decision=source_decision, approved_by=approved_by, approval_timestamp=approval_timestamp,
        action_title=action_title, action_description=action_description, category=category,
        action_type=action_type, owner=owner, accountable_leader=accountable_leader,
        stakeholders_json=json.dumps(stakeholders or []), priority=priority, risk_level=risk_level,
        dependencies_json=json.dumps(dependencies or []), due_date=due_date,
        evidence_requirements_json=json.dumps(evidence_requirements or []),
        expected_outcomes=expected_outcomes, success_metrics_json=json.dumps(success_metrics or []),
        status=STATUS_DRAFT, disclaimer=DISCLAIMER,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    _record_audit_event(
        db, tenant_id, row.id, from_status="", to_status=STATUS_DRAFT,
        changed_by=changed_by or approved_by, changed_by_role=changed_by_role, reason="Action created from approved source decision.",
    )
    db.commit()
    return row


def get_action(db: Session, tenant_id: str, action_id: int) -> GovernedAction | None:
    return db.query(GovernedAction).filter(
        GovernedAction.tenant_id == tenant_id, GovernedAction.id == action_id,
    ).first()


def list_actions(
    db: Session, tenant_id: str, *, status: str = "", owner: str = "", facility_id: str = "",
    source_type: str = "", risk_level: str = "", category: str = "",
) -> list[dict]:
    q = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id)
    if status:
        q = q.filter(GovernedAction.status == status)
    if owner:
        q = q.filter(GovernedAction.owner == owner)
    if facility_id:
        q = q.filter(GovernedAction.facility_id == facility_id)
    if source_type:
        q = q.filter(GovernedAction.source_type == source_type)
    if risk_level:
        q = q.filter(GovernedAction.risk_level == risk_level)
    if category:
        q = q.filter(GovernedAction.category == category)
    return [to_dict(r) for r in q.order_by(GovernedAction.created_at.desc()).all()]


def audit_history(db: Session, tenant_id: str, action_id: int) -> list[dict]:
    rows = (
        db.query(GovernedActionAuditEvent)
        .filter(GovernedActionAuditEvent.tenant_id == tenant_id, GovernedActionAuditEvent.governed_action_id == action_id)
        .order_by(GovernedActionAuditEvent.created_at.asc())
        .all()
    )
    return [_audit_to_dict(r) for r in rows]


def assign_owner(
    db: Session, tenant_id: str, action_id: int, *, owner: str, accountable_leader: str,
    changed_by: str, changed_by_role: str,
) -> GovernedAction:
    """Section 1/4: identify owners and stakeholders. Every action requires
    both an owner and an accountable leader before it can move past DRAFT."""
    action = get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    if not owner.strip() or not accountable_leader.strip():
        raise ValueError("A Governed Action requires both an owner and an accountable leader.")
    action.owner = owner
    action.accountable_leader = accountable_leader
    db.commit()
    db.refresh(action)
    _record_audit_event(
        db, tenant_id, action.id, from_status=action.status, to_status=action.status,
        changed_by=changed_by, changed_by_role=changed_by_role,
        reason=f"Owner assigned: {owner}; accountable leader: {accountable_leader}.",
    )
    db.commit()
    return action


def update_scope(
    db: Session, tenant_id: str, action_id: int, *, action_description: str | None = None,
    category: str | None = None, action_type: str | None = None, changed_by: str, changed_by_role: str,
) -> GovernedAction:
    """Section 27: Steward may not expand the scope of an approved action
    without new authorization -- any edit to what the action actually *is*
    (description, category, or type) requires a manager-tier-or-above
    actor, same threshold as approving a standard-risk action."""
    action = get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    if ROLE_AUTHORITY_TIER.get(changed_by_role, 0) < TIER_APPROVE_STANDARD:
        raise ValueError("Expanding a Governed Action's scope requires new, manager-tier-or-above authorization.")
    if action_description is not None:
        action.action_description = action_description
    if category is not None or action_type is not None:
        new_category = category or action.category
        new_type = action_type or action.action_type
        if new_category not in ACTION_TYPES_BY_CATEGORY:
            raise ValueError(f"Unknown action category: {new_category}")
        if new_type not in ACTION_TYPES_BY_CATEGORY[new_category]:
            raise ValueError(f"Action type '{new_type}' is not valid for category '{new_category}'")
        action.category = new_category
        action.action_type = new_type
    db.commit()
    db.refresh(action)
    _record_audit_event(
        db, tenant_id, action.id, from_status=action.status, to_status=action.status,
        changed_by=changed_by, changed_by_role=changed_by_role, reason="Action scope updated under new authorization.",
    )
    db.commit()
    return action


def transition_status(
    db: Session, tenant_id: str, action_id: int, *, new_status: str, changed_by: str, changed_by_role: str,
    reason: str = "", actor_facility_id: str = "",
) -> GovernedAction:
    """Section 3: every transition must be role-authorized and audited.
    APPROVED/CLOSED/CANCELLED are gated by authority tier (Section 27);
    approving/closing a high-risk action requires a higher tier than a
    standard-risk one. A non-admin-tier approver is also scope-limited to
    their own facility (Section 23: "supervisor can approve only within
    configured scope")."""
    action = get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    if action.status in TERMINAL_STATUSES:
        raise ValueError(f"Governed Action #{action_id} is {action.status} and cannot transition further.")
    if new_status not in ACTION_STATUSES:
        raise ValueError(f"Unknown status: {new_status}")

    if new_status in _GATED_TRANSITIONS:
        actor_tier = ROLE_AUTHORITY_TIER.get(changed_by_role, 0)
        required_tier = _required_tier(action, new_status)
        if actor_tier < required_tier:
            raise ValueError(
                f"Role '{changed_by_role}' (tier {actor_tier}) is not authorized to move this action to "
                f"{new_status}; requires tier {required_tier} or higher."
            )
        if actor_tier < TIER_CROSS_FACILITY_AUTHORITY and action.facility_id and actor_facility_id != action.facility_id:
            raise ValueError(
                "This approver's configured scope does not include this action's facility; "
                "only a director/executive-tier approver may act across facilities."
            )

    if new_status in (STATUS_READY_TO_START,) and (not action.owner.strip() or not action.accountable_leader.strip()):
        raise ValueError("A Governed Action requires both an owner and an accountable leader before it can start.")

    from_status = action.status
    action.status = new_status
    if new_status == STATUS_CLOSED:
        action.closed_at = datetime.now(timezone.utc)
        action.closure_approver = changed_by
    db.commit()
    db.refresh(action)
    _record_audit_event(
        db, tenant_id, action.id, from_status=from_status, to_status=new_status,
        changed_by=changed_by, changed_by_role=changed_by_role, reason=reason,
    )
    db.commit()
    return action
