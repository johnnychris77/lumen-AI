"""Project Steward, Section 22: Communication and Notification Plan.

Mirrors `council_notification_service.combined_notifications`'s exact
"compute and return a list of notification dicts" pattern -- Steward
introduces no new delivery channel of its own. Never includes clinical or
workforce detail beyond what the recipient's own role would already see
elsewhere in the workspace.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.governed_action import GovernedAction, STATUS_AWAITING_VERIFICATION, TERMINAL_STATUSES
from app.services import steward_escalation_service

_DUE_SOON_WINDOW_DAYS = 3


def _normalize(*, governed_action_id: int, message: str, recipient_role: str) -> dict:
    return {
        "source": "steward", "governed_action_id": governed_action_id, "message": message,
        "recipient_role": recipient_role, "read": False,
    }


def combined_notifications(db: Session, tenant_id: str, *, recipient_role: str = "", limit: int = 50) -> list[dict]:
    now = datetime.now(timezone.utc)
    items: list[dict] = []

    for escalation in steward_escalation_service.evaluate_escalations(db, tenant_id):
        items.append(_normalize(
            governed_action_id=escalation["governed_action_id"], message=escalation["message"],
            recipient_role=escalation["next_accountable_role"],
        ))

    actions = db.query(GovernedAction).filter(GovernedAction.tenant_id == tenant_id).all()
    for action in actions:
        if action.status in TERMINAL_STATUSES:
            continue
        if action.due_date:
            due = action.due_date if action.due_date.tzinfo else action.due_date.replace(tzinfo=timezone.utc)
            if now <= due <= now + timedelta(days=_DUE_SOON_WINDOW_DAYS):
                items.append(_normalize(
                    governed_action_id=action.id,
                    message=f"Governed Action #{action.id} ('{action.action_title}') is due soon.",
                    recipient_role="spd_manager",
                ))
        if action.status == STATUS_AWAITING_VERIFICATION:
            items.append(_normalize(
                governed_action_id=action.id,
                message=f"Governed Action #{action.id} ('{action.action_title}') is awaiting verification.",
                recipient_role="spd_manager",
            ))

    if recipient_role:
        items = [i for i in items if i["recipient_role"] == recipient_role]
    return items[:limit]
