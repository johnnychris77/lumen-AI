"""v4.5 — Project Orbit, Section 4: Cross-Department Coordination.

Reuses `or_connect_service.generate_stakeholder_notifications`/
`list_case_notifications`/`mark_notification_read` (Project Symphony's
existing recipient-role fan-out) rather than building a second
notification system. `or_connect.py`'s `STAKEHOLDER_ROLES` was extended
(not duplicated) with the three departments Symphony didn't already
cover — Infection Prevention, Quality, Biomedical Engineering — so all
seven named departments (SPD, OR, Supply Chain, Clinical Engineering,
Infection Prevention, Quality, Biomedical Engineering) route through the
one existing `CaseNotification` table.

"Each action is tracked through a shared operational timeline" (Section
4) is implemented here by merging `CaseNotification` and `CaseRiskAlert`
rows for a case into one ordered timeline — composing two already-real
tables, never a third event-of-record table.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.or_connect import CaseNotification, CaseRiskAlert, STAKEHOLDER_ROLES
from app.services import or_connect_service


def department_coordination_timeline(db: Session, tenant_id: str, case_id: int) -> dict:
    notifications = (
        db.query(CaseNotification)
        .filter(CaseNotification.tenant_id == tenant_id, CaseNotification.case_id == case_id)
        .all()
    )
    alerts = (
        db.query(CaseRiskAlert)
        .filter(CaseRiskAlert.tenant_id == tenant_id, CaseRiskAlert.case_id == case_id)
        .all()
    )

    timeline = [
        {
            "kind": "notification", "timestamp": n.created_at.isoformat(), "department": n.recipient_role,
            "message": n.message, "read": n.read,
        }
        for n in notifications
    ] + [
        {
            "kind": "risk_alert", "timestamp": a.created_at.isoformat(), "risk_type": a.risk_type,
            "severity": a.severity, "message": a.message, "resolved": a.resolved_at is not None,
        }
        for a in alerts
    ]
    timeline.sort(key=lambda i: i["timestamp"])

    return {
        "case_id": case_id, "departments": STAKEHOLDER_ROLES, "event_count": len(timeline), "timeline": timeline,
    }


def coordinate_case(db: Session, tenant_id: str, case_id: int) -> dict:
    """Detects operational risks and fans out stakeholder notifications
    across all seven departments in one call — the day-to-day entry point
    for Section 4's coordination workflows."""
    notifications = or_connect_service.generate_stakeholder_notifications(db, tenant_id, case_id)
    return {"case_id": case_id, "notifications_sent": len(notifications), "notifications": notifications}


def department_inbox(db: Session, tenant_id: str, *, department: str, unread_only: bool = False) -> dict:
    if department not in STAKEHOLDER_ROLES:
        raise ValueError(f"department must be one of {STAKEHOLDER_ROLES}")
    notifications = or_connect_service.list_case_notifications(db, tenant_id, recipient_role=department, unread_only=unread_only)
    return {"department": department, "notifications": notifications}
