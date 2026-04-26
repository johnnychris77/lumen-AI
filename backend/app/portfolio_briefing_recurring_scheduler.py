from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text

from app.db import session as db_session
from app.portfolio_briefing_schedules import (
    run_portfolio_briefing_schedule_now,
    ensure_portfolio_briefing_schedule_table,
)


_scheduler: BackgroundScheduler | None = None
_last_run_summary: dict[str, Any] = {
    "status": "not_started",
    "checked_at": None,
    "ran_schedule_ids": [],
    "errors": [],
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_db_session():
    if hasattr(db_session, "SessionLocal"):
        return db_session.SessionLocal()

    if hasattr(db_session, "sessionmaker"):
        return db_session.sessionmaker()

    raise RuntimeError("No SessionLocal provider found in app.db.session")


def ensure_recurring_schedule_columns(db) -> None:
    ensure_portfolio_briefing_schedule_table(db)

    db.execute(
        text(
            """
            ALTER TABLE portfolio_briefing_schedules
            ADD COLUMN IF NOT EXISTS interval_minutes INTEGER NOT NULL DEFAULT 43200
            """
        )
    )

    db.execute(
        text(
            """
            ALTER TABLE portfolio_briefing_schedules
            ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMP WITH TIME ZONE
            """
        )
    )

    db.execute(
        text(
            """
            UPDATE portfolio_briefing_schedules
            SET next_run_at = COALESCE(next_run_at, NOW())
            WHERE is_enabled = TRUE
            """
        )
    )

    db.commit()


def run_due_portfolio_briefing_schedules() -> dict[str, Any]:
    global _last_run_summary

    db = _new_db_session()
    checked_at = _utc_now()
    ran_schedule_ids: list[int] = []
    errors: list[dict[str, Any]] = []

    try:
        ensure_recurring_schedule_columns(db)

        rows = (
            db.execute(
                text(
                    """
                    SELECT *
                    FROM portfolio_briefing_schedules
                    WHERE is_enabled = TRUE
                      AND COALESCE(next_run_at, NOW()) <= NOW()
                    ORDER BY next_run_at ASC NULLS FIRST, id ASC
                    """
                )
            )
            .mappings()
            .all()
        )

        for row in rows:
            schedule = dict(row)
            schedule_id = int(schedule["id"])
            interval_minutes = int(schedule.get("interval_minutes") or 43200)

            try:
                run_portfolio_briefing_schedule_now(db, schedule_id)
                ran_schedule_ids.append(schedule_id)

                db.execute(
                    text(
                        """
                        UPDATE portfolio_briefing_schedules
                        SET next_run_at = NOW() + (:interval_minutes * INTERVAL '1 minute')
                        WHERE id = :schedule_id
                        """
                    ),
                    {
                        "schedule_id": schedule_id,
                        "interval_minutes": interval_minutes,
                    },
                )
                db.commit()

            except Exception as exc:
                db.rollback()
                errors.append(
                    {
                        "schedule_id": schedule_id,
                        "error": repr(exc),
                    }
                )

        _last_run_summary = {
            "status": "completed",
            "checked_at": checked_at.isoformat(),
            "ran_schedule_ids": ran_schedule_ids,
            "due_count": len(rows),
            "run_count": len(ran_schedule_ids),
            "errors": errors,
        }

        return _last_run_summary

    finally:
        db.close()


def start_recurring_portfolio_briefing_scheduler() -> dict[str, Any]:
    global _scheduler

    if _scheduler and _scheduler.running:
        return scheduler_status()

    interval_seconds = int(os.getenv("PORTFOLIO_BRIEFING_SCHEDULER_SECONDS", "60"))

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        run_due_portfolio_briefing_schedules,
        "interval",
        seconds=interval_seconds,
        id="portfolio_briefing_due_schedule_runner",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()

    return scheduler_status()


def shutdown_recurring_portfolio_briefing_scheduler() -> None:
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def scheduler_status() -> dict[str, Any]:
    return {
        "running": bool(_scheduler and _scheduler.running),
        "jobs": [
            {
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in (_scheduler.get_jobs() if _scheduler else [])
        ],
        "last_run_summary": _last_run_summary,
    }
