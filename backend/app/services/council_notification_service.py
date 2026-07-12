"""Project Council, Section 18: Notifications and Escalations.

Surfaces Council-specific notification-worthy conditions (safety dissent,
insufficient evidence, urgent cases, overdue human decisions, unresolved
split decisions, missing required specialists, outcome reviews due,
Council configuration changes) in the same normalized shape as the
existing platform notification feed (`platform_notification_service.
unified_notifications`), and merges the two -- reusing the existing
notification channel rather than inventing a parallel one. Council items
are computed live from its own tables, never persisted as a fourth
notification store.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.council_leadership import (
    CASE_STATUS_AWAITING_DECISION,
    CASE_STATUS_RESOLVED,
    CONSENSUS_INSUFFICIENT_EVIDENCE,
    CONSENSUS_SAFETY_DISSENT,
    CONSENSUS_SPLIT,
    CouncilCase,
    CouncilOutcomeReview,
    CouncilTeamConfig,
)
from app.services.platform_notification_service import unified_notifications

_OVERDUE_DECISION_HOURS = 48
_OUTCOME_REVIEW_DUE_DAYS = 14


def _normalize(*, id_: int, created_at, message: str, recipient_role: str = "") -> dict:
    return {
        "source": "council",
        "id": id_,
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
        "message": message,
        "read": False,
        "recipient_role": recipient_role,
    }


def council_notification_items(db: Session, tenant_id: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    items: list[dict] = []

    cases = db.query(CouncilCase).filter(CouncilCase.tenant_id == tenant_id).all()
    for case in cases:
        if case.consensus_status == CONSENSUS_SAFETY_DISSENT:
            items.append(_normalize(id_=case.id, created_at=case.created_at, message=f"Council Case #{case.id}: unresolved safety dissent requires review.", recipient_role="spd_manager"))
        if case.consensus_status == CONSENSUS_INSUFFICIENT_EVIDENCE:
            items.append(_normalize(id_=case.id, created_at=case.created_at, message=f"Council Case #{case.id}: insufficient evidence to reach a recommendation.", recipient_role="spd_manager"))
        if case.urgency == "urgent" and case.status != CASE_STATUS_RESOLVED:
            items.append(_normalize(id_=case.id, created_at=case.created_at, message=f"Council Case #{case.id}: urgent case still open.", recipient_role="spd_manager"))
        if case.consensus_status == CONSENSUS_SPLIT:
            items.append(_normalize(id_=case.id, created_at=case.created_at, message=f"Council Case #{case.id}: unresolved split decision.", recipient_role="spd_manager"))
        if case.status == CASE_STATUS_AWAITING_DECISION:
            created_at = case.created_at if case.created_at.tzinfo else case.created_at.replace(tzinfo=timezone.utc)
            if now - created_at > timedelta(hours=_OVERDUE_DECISION_HOURS):
                items.append(_normalize(id_=case.id, created_at=case.created_at, message=f"Council Case #{case.id}: human decision overdue.", recipient_role="spd_manager"))

    reviewed_case_ids = {o.council_case_id for o in db.query(CouncilOutcomeReview).filter(CouncilOutcomeReview.tenant_id == tenant_id).all()}
    for case in cases:
        if case.status == CASE_STATUS_RESOLVED and case.id not in reviewed_case_ids:
            created_at = case.created_at if case.created_at.tzinfo else case.created_at.replace(tzinfo=timezone.utc)
            if now - created_at > timedelta(days=_OUTCOME_REVIEW_DUE_DAYS):
                items.append(_normalize(id_=case.id, created_at=case.created_at, message=f"Council Case #{case.id}: outcome effectiveness review is due.", recipient_role="spd_manager"))

    for config in db.query(CouncilTeamConfig).filter(CouncilTeamConfig.tenant_id == tenant_id, CouncilTeamConfig.approval_status == "pending_review").all():
        items.append(_normalize(id_=config.id, created_at=config.created_at, message=f"Council team '{config.team_key}' configuration change (v{config.version}) is pending review.", recipient_role="admin"))

    return items


def combined_notifications(db: Session, tenant_id: str, *, recipient_role: str = "", limit: int = 50) -> list[dict]:
    items = unified_notifications(db, tenant_id, recipient_role=recipient_role, limit=limit)
    council_items = council_notification_items(db, tenant_id)
    if recipient_role:
        council_items = [i for i in council_items if i["recipient_role"] == recipient_role]
    items.extend(council_items)
    items.sort(key=lambda i: i["created_at"] or "", reverse=True)
    return items[:limit]
