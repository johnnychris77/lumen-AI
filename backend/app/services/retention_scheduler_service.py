from __future__ import annotations

import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import SessionLocal
from app.notifications.retention_notifications import notify_retention_event
from app.services.retention_enforcement import enforce_retention_once

_scheduler: BackgroundScheduler | None = None


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _run_scheduled_retention():
    db = SessionLocal()
    try:
        summary = enforce_retention_once(db)

        blocked = int(summary.get("totals", {}).get("retention_blocks", 0) or 0)
        failures = int(summary.get("totals", {}).get("failures", 0) or 0)

        notify_blocked = _truthy(os.getenv("LUMENAI_RETENTION_NOTIFY_ON_BLOCKED", "true"))
        notify_failed = _truthy(os.getenv("LUMENAI_RETENTION_NOTIFY_ON_FAILURE", "true"))

        should_notify = (notify_blocked and blocked > 0) or (notify_failed and failures > 0)

        if should_notify:
            notify_retention_event(summary)
    finally:
        db.close()


def start_retention_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    if not _truthy(os.getenv("LUMENAI_RETENTION_ENFORCEMENT_ENABLED", "false")):
        return

    cron_expr = os.getenv("LUMENAI_RETENTION_ENFORCEMENT_CRON", "0 2 * * *").strip()
    parts = cron_expr.split()
    if len(parts) != 5:
        return

    minute, hour, day, month, day_of_week = parts

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _run_scheduled_retention,
        CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week),
        id="lumenai_retention_enforcement",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler


def retention_scheduler_running() -> bool:
    return _scheduler is not None and _scheduler.running
