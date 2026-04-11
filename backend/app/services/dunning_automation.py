from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import SessionLocal, models
from app.dunning import renewal_health_summary, suspend_if_past_due, mark_payment_success
from app.notifications.dunning_notifications import send_dunning_notification
from app.subscription_lifecycle import renew_subscription

_scheduler: BackgroundScheduler | None = None


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _grace_days() -> int:
    return int(os.getenv("LUMENAI_DUNNING_GRACE_DAYS", "7").strip() or 7)


def _find_active_subscriptions(db):
    return (
        db.query(models.TenantSubscription)
        .filter(models.TenantSubscription.status.in_(["active", "suspended"]))
        .all()
    )


def run_dunning_automation_once() -> dict:
    db = SessionLocal()
    try:
        results = []
        for sub in _find_active_subscriptions(db):
            health = renewal_health_summary(db, sub.tenant_id)
            if not health:
                continue

            item = {
                "tenant_id": sub.tenant_id,
                "tenant_name": sub.tenant_name,
                "actions": [],
            }

            if health["days_to_renewal"] <= 3 and sub.last_payment_status == "current":
                notif = send_dunning_notification(health, "renewal_due")
                item["actions"].append({"type": "renewal_due_notification", "notification": notif})

            if sub.last_payment_status == "failed":
                notif = send_dunning_notification(health, "payment_failed")
                item["actions"].append({"type": "payment_failed_notification", "notification": notif})

                suspension = suspend_if_past_due(db, sub.tenant_id, grace_days=_grace_days())
                item["actions"].append({"type": "suspension_check", "result": suspension})

                if suspension.get("suspended"):
                    notif2 = send_dunning_notification(suspension, "suspended")
                    item["actions"].append({"type": "suspension_notification", "notification": notif2})

            if sub.last_payment_status == "current" and sub.status == "active" and _now() >= sub.current_period_end:
                renewed = renew_subscription(db, tenant_id=sub.tenant_id, actor_email="system@lumenai.local", notes="Automated renewal")
                item["actions"].append({"type": "auto_renewal", "result": renewed})

            results.append(item)

        return {
            "evaluated_at": _now().isoformat(),
            "items": results,
        }
    finally:
        db.close()


def run_recovery_action_once(tenant_id: str) -> dict:
    db = SessionLocal()
    try:
        if not _truthy(os.getenv("LUMENAI_DUNNING_RECOVERY_ACTIONS_ENABLED", "true")):
            return {"enabled": False, "tenant_id": tenant_id}

        result = mark_payment_success(db, tenant_id, notes="Automated recovery")
        notif = send_dunning_notification(result, "recovered")
        return {
            "enabled": True,
            "tenant_id": tenant_id,
            "result": result,
            "notification": notif,
        }
    finally:
        db.close()


def start_dunning_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    if not _truthy(os.getenv("LUMENAI_DUNNING_AUTOMATION_ENABLED", "false")):
        return

    cron_expr = os.getenv("LUMENAI_DUNNING_CHECK_CRON", "0 */6 * * *").strip()
    parts = cron_expr.split()
    if len(parts) != 5:
        return

    minute, hour, day, month, day_of_week = parts

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_dunning_automation_once,
        CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week),
        id="lumenai_dunning_automation",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler


def dunning_scheduler_running() -> bool:
    return _scheduler is not None and _scheduler.running
