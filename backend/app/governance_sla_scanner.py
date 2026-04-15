from __future__ import annotations

import os
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import SessionLocal, models
from app.governance_sla import run_sla_evaluation, sla_dashboard

_scheduler: BackgroundScheduler | None = None
_last_run: dict = {}


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tenant_rows(db):
    rows = (
        db.query(models.GovernanceSlaPolicy.tenant_id, models.GovernanceSlaPolicy.tenant_name)
        .filter(models.GovernanceSlaPolicy.is_enabled == True)
        .distinct()
        .all()
    )
    return rows


def recommendation_for_event(event: models.GovernanceSlaEvent) -> str:
    if event.policy_key == "pending_packet_release":
        return "Review and approve, reject, or request corrections for the pending packet release."
    if event.policy_key == "active_release_hold":
        return "Review the compliance hold, document the required action, then clear the hold or create an emergency override."
    if event.policy_key == "blocked_packet_delivery":
        return "Review release approval, active holds, distribution list governance, and delivery configuration."
    if event.policy_key == "failed_packet_delivery":
        return "Verify delivery channel configuration, recipient target, and alert/email service settings."
    return "Review the governance exception and document the corrective action."


def run_scanner_once() -> dict:
    db = SessionLocal()
    try:
        results = []
        for tenant_id, tenant_name in _tenant_rows(db):
            result = run_sla_evaluation(db, tenant_id, tenant_name)
            results.append(result)

        global _last_run
        _last_run = {
            "ran_at": _now(),
            "tenant_count": len(results),
            "results": results,
        }
        return _last_run
    finally:
        db.close()


def scanner_status() -> dict:
    return {
        "enabled": _truthy(os.getenv("LUMENAI_GOVERNANCE_SLA_SCANNER_ENABLED", "false")),
        "cron": os.getenv("LUMENAI_GOVERNANCE_SLA_SCANNER_CRON", "0 */6 * * *"),
        "scheduler_running": bool(_scheduler and _scheduler.running),
        "last_run": _last_run,
    }


def scanner_recommendations(tenant_id: str, tenant_name: str) -> dict:
    db = SessionLocal()
    try:
        dashboard = sla_dashboard(db, tenant_id, tenant_name)
        events = (
            db.query(models.GovernanceSlaEvent)
            .filter(
                models.GovernanceSlaEvent.tenant_id == tenant_id,
                models.GovernanceSlaEvent.status == "open",
            )
            .order_by(models.GovernanceSlaEvent.id.desc())
            .limit(100)
            .all()
        )

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant_name,
            "open_count": len(events),
            "dashboard": dashboard,
            "items": [
                {
                    "event_id": e.id,
                    "policy_key": e.policy_key,
                    "resource_type": e.resource_type,
                    "resource_id": e.resource_id,
                    "severity": e.severity,
                    "age_hours": e.age_hours,
                    "recommendation": recommendation_for_event(e),
                    "details_json": e.details_json,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ],
        }
    finally:
        db.close()


def start_governance_sla_scanner() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    if not _truthy(os.getenv("LUMENAI_GOVERNANCE_SLA_SCANNER_ENABLED", "false")):
        return

    cron_expr = os.getenv("LUMENAI_GOVERNANCE_SLA_SCANNER_CRON", "0 */6 * * *").strip()
    parts = cron_expr.split()
    if len(parts) != 5:
        return

    minute, hour, day, month, day_of_week = parts

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        run_scanner_once,
        CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week),
        id="lumenai_governance_sla_scanner",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler
