"""Project Steward, Section 14: Leadership Action Boards -- role-specific
views over the same underlying Governed Action data."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.governed_action import (
    BENEFITS_ACHIEVED,
    BENEFITS_EXCEEDED,
    CATEGORY_CLINICAL_QUALITY,
    CATEGORY_EDUCATION,
    GovernedAction,
    STATUS_AWAITING_EVIDENCE,
    STATUS_BLOCKED,
    TERMINAL_STATUSES,
)
from app.services import steward_action_service


def supervisor_board(db: Session, tenant_id: str, *, facility_id: str = "") -> dict:
    q = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id, GovernedAction.status.notin_(TERMINAL_STATUSES))
    if facility_id:
        q = q.filter(GovernedAction.facility_id == facility_id)
    actions = q.all()
    return {
        "actions_assigned_to_shift": [steward_action_service.to_dict(a) for a in actions if a.owner],
        "education_completion": [steward_action_service.to_dict(a) for a in actions if a.category == CATEGORY_EDUCATION],
        "inspection_changes": [steward_action_service.to_dict(a) for a in actions if a.category == CATEGORY_CLINICAL_QUALITY],
        "evidence_due": [steward_action_service.to_dict(a) for a in actions if a.status == STATUS_AWAITING_EVIDENCE],
    }


def manager_board(db: Session, tenant_id: str) -> dict:
    actions = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id, GovernedAction.status.notin_(TERMINAL_STATUSES)).all()
    owner_counts = Counter(a.owner for a in actions if a.owner)
    return {
        "department_actions": [steward_action_service.to_dict(a) for a in actions],
        "blocked_work": [steward_action_service.to_dict(a) for a in actions if a.status == STATUS_BLOCKED],
        "owner_performance": dict(owner_counts),
        "implementation_risk": [steward_action_service.to_dict(a) for a in actions if a.risk_level in ("high", "critical")],
    }


def director_board(db: Session, tenant_id: str) -> dict:
    actions = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id, GovernedAction.status.notin_(TERMINAL_STATUSES)).all()
    facilities = {a.facility_id for a in actions if a.facility_id}
    return {
        "cross_facility_actions": [steward_action_service.to_dict(a) for a in actions if len(facilities) > 1],
        "high_risk_changes": [steward_action_service.to_dict(a) for a in actions if a.risk_level in ("high", "critical")],
        "resource_requirements": [steward_action_service.to_dict(a) for a in actions if a.category == "operational"],
        "benefits_realization": [steward_action_service.to_dict(a) for a in actions if a.benefits_realization],
    }


def executive_board(db: Session, tenant_id: str) -> dict:
    now = datetime.now(timezone.utc)
    actions = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id).all()
    active = [a for a in actions if a.status not in TERMINAL_STATUSES]

    def _is_overdue(a: GovernedAction) -> bool:
        if not a.due_date:
            return False
        due = a.due_date if a.due_date.tzinfo else a.due_date.replace(tzinfo=timezone.utc)
        return due < now

    return {
        "strategic_initiatives": [steward_action_service.to_dict(a) for a in active if a.category == "governance"],
        "enterprise_risk_reduction": [steward_action_service.to_dict(a) for a in active if a.risk_level in ("high", "critical")],
        "overdue_critical_actions": [steward_action_service.to_dict(a) for a in active if a.risk_level == "critical" and _is_overdue(a)],
        "achieved_value": [steward_action_service.to_dict(a) for a in actions if a.benefits_realization in (BENEFITS_ACHIEVED, BENEFITS_EXCEEDED)],
        "unresolved_barriers": [steward_action_service.to_dict(a) for a in active if a.status == STATUS_BLOCKED],
    }
