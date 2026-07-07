"""v1.7 — Notification Framework (Deliverable 10).

An in-app, per-role/per-person notification queue for workflow events —
distinct from the existing Slack/Teams/email AlertEvent dispatcher in
app/notifications/notifier.py (external channels for critical-finding
alerts, unrelated to per-inspection workflow tracking). Notifications here
are generated from real, already-computed queue/escalation state and are
idempotent per inspection+type so re-running generation never duplicates
an already-emitted notification.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.workflow import WorkflowNotification

NOTIFICATION_TYPES = [
    "inspection_assigned", "supervisor_review_required", "critical_finding",
    "repair_recommendation", "inspection_overdue", "coverage_incomplete",
]

_OVERDUE_MINUTES_THRESHOLD = 480  # 8h
_COVERAGE_INCOMPLETE_THRESHOLD = 75


def notify(
    db: Session, *, tenant_id: str, inspection_id: int, notification_type: str,
    recipient_role: str, message: str, recipient_name: str = "",
) -> WorkflowNotification:
    row = WorkflowNotification(
        tenant_id=tenant_id, inspection_id=inspection_id, notification_type=notification_type,
        recipient_role=recipient_role, recipient_name=recipient_name, message=message,
    )
    db.add(row)
    return row


def _already_notified(db: Session, tenant_id: str, inspection_id: int, notification_type: str) -> bool:
    return (
        db.query(WorkflowNotification.id)
        .filter(
            WorkflowNotification.tenant_id == tenant_id, WorkflowNotification.inspection_id == inspection_id,
            WorkflowNotification.notification_type == notification_type,
        )
        .first()
        is not None
    )


def list_notifications(
    db: Session, tenant_id: str, *, recipient_role: str, unread_only: bool = False,
) -> list[WorkflowNotification]:
    q = db.query(WorkflowNotification).filter(
        WorkflowNotification.tenant_id == tenant_id, WorkflowNotification.recipient_role == recipient_role,
    )
    if unread_only:
        q = q.filter(WorkflowNotification.read.is_(False))
    return q.order_by(WorkflowNotification.id.desc()).all()


def mark_read(db: Session, tenant_id: str, notification_id: int) -> WorkflowNotification | None:
    row = (
        db.query(WorkflowNotification)
        .filter(WorkflowNotification.tenant_id == tenant_id, WorkflowNotification.id == notification_id)
        .first()
    )
    if row is None:
        return None
    row.read = True
    row.read_at = datetime.now(timezone.utc)
    return row


def generate_workflow_notifications(db: Session, tenant_id: str) -> dict:
    """Deliverable 10 — scan real queue/escalation state and emit a
    notification for each event not already emitted."""
    from app.services.work_queue_service import build_work_queue

    created = 0
    queue = build_work_queue(db, tenant_id)

    def _emit(item: dict, notification_type: str, recipient_role: str, message: str) -> None:
        nonlocal created
        if not _already_notified(db, tenant_id, item["inspection_id"], notification_type):
            notify(
                db, tenant_id=tenant_id, inspection_id=item["inspection_id"],
                notification_type=notification_type, recipient_role=recipient_role, message=message,
            )
            created += 1

    for item in queue["supervisor_reviews"]:
        _emit(
            item, "supervisor_review_required", "spd_manager",
            f"Inspection #{item['inspection_id']} ({item['instrument_type']}) requires supervisor review.",
        )

    for item in queue["repair_holds"]:
        _emit(
            item, "repair_recommendation", "spd_manager",
            f"Inspection #{item['inspection_id']} ({item['instrument_type']}) recommended for repair evaluation.",
        )

    for item in queue["high_risk_inspections"]:
        _emit(
            item, "critical_finding", "spd_manager",
            f"Critical finding on inspection #{item['inspection_id']} ({item['instrument_type']}).",
        )

    for item in queue["pending_inspections"]:
        if item["minutes_waiting"] is not None and item["minutes_waiting"] > _OVERDUE_MINUTES_THRESHOLD:
            _emit(
                item, "inspection_overdue", "spd_manager",
                f"Inspection #{item['inspection_id']} has been waiting {item['minutes_waiting']} minutes.",
            )
        if item["coverage_pct"] is not None and item["coverage_pct"] < _COVERAGE_INCOMPLETE_THRESHOLD:
            _emit(
                item, "coverage_incomplete", "operator",
                f"Inspection #{item['inspection_id']} coverage is only {item['coverage_pct']}% — capture remaining zones.",
            )

    db.commit()
    return {"notifications_created": created, "human_review_required": True}
