"""Project Steward, Section 23: Action Escalation Rules.

Every escalation identifies the next accountable role -- standard-risk
actions escalate to a manager-tier role (`spd_manager`), unresolved
high-risk/critical situations escalate all the way to director/executive-
tier (`admin`), mirroring the real 4-role RBAC's ceiling.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.governed_action import (
    BENEFITS_WORSENED,
    GovernedAction,
    STATUS_AWAITING_EVIDENCE,
    STATUS_BLOCKED,
    TERMINAL_STATUSES,
)
from app.services import steward_unintended_consequence_service, steward_verification_service


def _next_accountable_role(action: GovernedAction) -> str:
    return "admin" if action.risk_level in ("high", "critical") else "spd_manager"


def evaluate_escalations_for_action(db: Session, tenant_id: str, action: GovernedAction) -> list[dict]:
    now = datetime.now(timezone.utc)
    items: list[dict] = []
    next_role = _next_accountable_role(action)

    if action.status in TERMINAL_STATUSES:
        return items

    if action.risk_level == "critical" and action.due_date:
        due = action.due_date if action.due_date.tzinfo else action.due_date.replace(tzinfo=timezone.utc)
        if due < now:
            items.append({
                "governed_action_id": action.id, "rule": "critical_action_overdue",
                "message": f"Governed Action #{action.id} ('{action.action_title}') is critical and overdue.",
                "next_accountable_role": next_role,
            })

    if not action.owner.strip():
        items.append({
            "governed_action_id": action.id, "rule": "no_owner",
            "message": f"Governed Action #{action.id} ('{action.action_title}') has no assigned owner.",
            "next_accountable_role": next_role,
        })

    if action.status == STATUS_BLOCKED:
        items.append({
            "governed_action_id": action.id, "rule": "resource_dependency_blocks_action",
            "message": f"Governed Action #{action.id} ('{action.action_title}') is blocked.",
            "next_accountable_role": next_role,
        })

    if action.status == STATUS_AWAITING_EVIDENCE and not steward_verification_service.has_sufficient_evidence(db, tenant_id, action.id):
        items.append({
            "governed_action_id": action.id, "rule": "required_evidence_unavailable",
            "message": f"Governed Action #{action.id} ('{action.action_title}') is awaiting required evidence.",
            "next_accountable_role": next_role,
        })

    if action.benefits_realization == BENEFITS_WORSENED:
        items.append({
            "governed_action_id": action.id, "rule": "action_outcome_worsened",
            "message": f"Governed Action #{action.id} ('{action.action_title}') measured outcome has worsened.",
            "next_accountable_role": "admin",
        })

    unreviewed = [c for c in steward_unintended_consequence_service.list_consequences(db, tenant_id, action.id) if not c["reviewed"]]
    if unreviewed:
        items.append({
            "governed_action_id": action.id, "rule": "unreviewed_unintended_consequence",
            "message": f"Governed Action #{action.id} ('{action.action_title}') has an unreviewed unintended consequence.",
            "next_accountable_role": next_role,
        })

    return items


def evaluate_escalations(db: Session, tenant_id: str) -> list[dict]:
    actions = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id).all()
    items: list[dict] = []
    for action in actions:
        items.extend(evaluate_escalations_for_action(db, tenant_id, action))
    return items
