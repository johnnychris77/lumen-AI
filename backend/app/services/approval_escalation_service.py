from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import SessionLocal, models
from app.notifications.approval_notifications import notify_approval

_scheduler: BackgroundScheduler | None = None


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def find_stale_approvals(db, hours: int) -> list[models.GovernanceApproval]:
    cutoff = _now() - timedelta(hours=hours)
    return (
        db.query(models.GovernanceApproval)
        .filter(
            models.GovernanceApproval.status == "pending",
            models.GovernanceApproval.created_at < cutoff,
        )
        .order_by(models.GovernanceApproval.id.asc())
        .all()
    )


def _approval_response(row: models.GovernanceApproval) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "request_type": row.request_type,
        "target_resource": row.target_resource,
        "target_resource_id": row.target_resource_id,
        "requested_by": row.requested_by,
        "requested_role": row.requested_role,
        "requested_payload": row.requested_payload,
        "status": row.status,
        "reviewed_by": row.reviewed_by,
        "review_notes": row.review_notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
    }


def run_approval_escalation_once() -> dict:
    db = SessionLocal()
    try:
        hours = int(os.getenv("LUMENAI_APPROVAL_ESCALATION_HOURS", "24").strip() or 24)
        rows = find_stale_approvals(db, hours)
        results = []
        for row in rows:
            results.append({
                "approval_id": row.id,
                "notification": notify_approval(_approval_response(row), mode="escalation"),
            })
        return {
            "evaluated_at": _now().isoformat(),
            "escalation_hours": hours,
            "stale_count": len(rows),
            "results": results,
        }
    finally:
        db.close()


def start_approval_escalation_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    if not _truthy(os.getenv("LUMENAI_APPROVAL_NOTIFICATIONS_ENABLED", "false")):
        return

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_approval_escalation_once,
        CronTrigger(minute="0", hour="*/1"),
        id="lumenai_approval_escalation",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler


def approval_escalation_scheduler_running() -> bool:
    return _scheduler is not None and _scheduler.running
