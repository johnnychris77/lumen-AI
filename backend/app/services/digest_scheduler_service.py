from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import SessionLocal, models
from app.notifications.digest_delivery import deliver_digest

_scheduler: BackgroundScheduler | None = None


def _truthy(v: str | None) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "on"}


def _site_name(row: models.Inspection) -> str:
    return (getattr(row, "site_name", None) or "default-site").strip() or "default-site"


def _vendor_name(row: models.Inspection) -> str:
    return (getattr(row, "vendor_name", None) or "unknown").strip() or "unknown"


def _issue_name(row: models.Inspection) -> str:
    return (getattr(row, "detected_issue", None) or "unknown").strip() or "unknown"


def _top_counts(counter: dict[str, int], limit: int = 10):
    return sorted(
        [{"label": k, "count": v} for k, v in counter.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:limit]


def _within_days(dt: datetime | None, days: int) -> bool:
    if not dt:
        return False
    now = datetime.now(timezone.utc)
    return dt >= now - timedelta(days=days)


def _rows_for_window(days: int):
    db = SessionLocal()
    try:
        rows = db.query(models.Inspection).order_by(models.Inspection.id.desc()).all()
        return [r for r in rows if _within_days(r.created_at, days)]
    finally:
        db.close()


def _build_digest(rows: list[models.Inspection]) -> dict:
    total = len(rows)
    completed = sum(1 for r in rows if (r.status or "").lower() == "completed")
    open_alerts = sum(1 for r in rows if (getattr(r, "alert_status", "open") or "").lower() != "resolved")
    resolved_alerts = sum(1 for r in rows if (getattr(r, "alert_status", "") or "").lower() == "resolved")
    high_risk_count = sum(1 for r in rows if int(getattr(r, "risk_score", 0) or 0) >= 80)
    qa_reviewed = sum(1 for r in rows if (getattr(r, "qa_review_status", "") or "").lower() in {"approved", "overridden"})
    qa_overridden = sum(1 for r in rows if (getattr(r, "qa_review_status", "") or "").lower() == "overridden")

    site_counter: dict[str, int] = {}
    vendor_counter: dict[str, int] = {}
    issue_counter: dict[str, int] = {}

    for r in rows:
        site = _site_name(r)
        vendor = _vendor_name(r)
        issue = _issue_name(r)
        site_counter[site] = site_counter.get(site, 0) + 1
        vendor_counter[vendor] = vendor_counter.get(vendor, 0) + 1
        issue_counter[issue] = issue_counter.get(issue, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": {
            "total_inspections": total,
            "completed": completed,
            "completion_rate": round(completed / total, 4) if total else 0.0,
            "open_alerts": open_alerts,
            "resolved_alerts": resolved_alerts,
            "high_risk_count": high_risk_count,
            "qa_reviewed": qa_reviewed,
            "qa_overridden": qa_overridden,
            "qa_override_rate": round(qa_overridden / qa_reviewed, 4) if qa_reviewed else 0.0,
            "top_sites": _top_counts(site_counter),
            "top_vendors": _top_counts(vendor_counter),
            "top_issues": _top_counts(issue_counter),
        },
        "leadership_narrative": {
            "headline": f"{total} inspections processed in reporting window with {open_alerts} open alerts and {high_risk_count} high-risk findings.",
            "quality_note": f"QA reviewed {qa_reviewed} cases with an override rate of {round((qa_overridden / qa_reviewed) * 100, 1) if qa_reviewed else 0.0}%.",
            "operations_note": f"Top issue trend: {(_top_counts(issue_counter, 1)[0]['label'] if issue_counter else 'none')} | Top site by volume: {(_top_counts(site_counter, 1)[0]['label'] if site_counter else 'none')}.",
        }
    }


def _run_scheduled_digest():
    db = SessionLocal()
    try:
        days = int(os.getenv("LUMENAI_DIGEST_AUTOMATION_WINDOW_DAYS", "7").strip() or 7)
        rows = _rows_for_window(days)
        digest = _build_digest(rows)
        deliver_digest(db, digest_type="weekly", digest_payload=digest)
    finally:
        db.close()


def start_digest_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return

    if not _truthy(os.getenv("LUMENAI_DIGEST_AUTOMATION_ENABLED", "false")):
        return

    cron_expr = os.getenv("LUMENAI_DIGEST_AUTOMATION_CRON", "0 7 * * MON").strip()
    parts = cron_expr.split()
    if len(parts) != 5:
        return

    minute, hour, day, month, day_of_week = parts

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        _run_scheduled_digest,
        CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week),
        id="lumenai_weekly_digest",
        replace_existing=True,
    )
    scheduler.start()
    _scheduler = scheduler


def scheduler_running() -> bool:
    return _scheduler is not None and _scheduler.running
