"""Project Steward, Section 12: the `/steward` Workspace payload."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.governed_action import (
    BENEFITS_ACHIEVED,
    BENEFITS_EXCEEDED,
    GovernedAction,
    STATUS_APPROVED,
    STATUS_AT_RISK,
    STATUS_AWAITING_EVIDENCE,
    STATUS_AWAITING_VERIFICATION,
    STATUS_BLOCKED,
    STATUS_CLOSED,
    STATUS_COMPLETED_PENDING_REVIEW,
    TERMINAL_STATUSES,
)
from app.services import steward_action_service, steward_unintended_consequence_service

_DUE_SOON_WINDOW_DAYS = 7
_RECENT_CLOSURE_WINDOW_DAYS = 30


def workspace_summary(db: Session, tenant_id: str) -> dict:
    now = datetime.now(timezone.utc)
    all_actions = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id).all()
    active = [a for a in all_actions if a.status not in TERMINAL_STATUSES]

    def due_within(days: int) -> list[GovernedAction]:
        out = []
        for a in active:
            if not a.due_date:
                continue
            due = a.due_date if a.due_date.tzinfo else a.due_date.replace(tzinfo=timezone.utc)
            if now <= due <= now + timedelta(days=days):
                out.append(a)
        return out

    actions_with_consequences = {
        a.id for a in active
        if any(not c["reviewed"] for c in steward_unintended_consequence_service.list_consequences(db, tenant_id, a.id))
    }

    recent_cutoff = now - timedelta(days=_RECENT_CLOSURE_WINDOW_DAYS)
    recently_closed = [
        a for a in all_actions
        if a.status == STATUS_CLOSED and a.closed_at and (a.closed_at if a.closed_at.tzinfo else a.closed_at.replace(tzinfo=timezone.utc)) >= recent_cutoff
    ]

    return {
        "approved_actions": [steward_action_service.to_dict(a) for a in active if a.status == STATUS_APPROVED],
        "actions_awaiting_owner": [steward_action_service.to_dict(a) for a in active if not a.owner.strip()],
        "actions_due_soon": [steward_action_service.to_dict(a) for a in due_within(_DUE_SOON_WINDOW_DAYS)],
        "blocked_actions": [steward_action_service.to_dict(a) for a in active if a.status == STATUS_BLOCKED],
        "actions_at_risk": [steward_action_service.to_dict(a) for a in active if a.status == STATUS_AT_RISK],
        "evidence_missing": [steward_action_service.to_dict(a) for a in active if a.status == STATUS_AWAITING_EVIDENCE],
        "verification_pending": [steward_action_service.to_dict(a) for a in active if a.status == STATUS_AWAITING_VERIFICATION],
        "benefits_not_achieved": [
            steward_action_service.to_dict(a) for a in active
            if a.benefits_realization and a.benefits_realization not in (BENEFITS_ACHIEVED, BENEFITS_EXCEEDED)
        ],
        "unintended_consequences": [steward_action_service.to_dict(a) for a in active if a.id in actions_with_consequences],
        "actions_ready_for_closure": [steward_action_service.to_dict(a) for a in active if a.status == STATUS_COMPLETED_PENDING_REVIEW],
        "recently_closed_actions": [steward_action_service.to_dict(a) for a in recently_closed],
        "human_review_required": True,
    }
