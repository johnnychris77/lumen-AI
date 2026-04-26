from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.portfolio_briefing_exports import (
    build_portfolio_briefing_export,
    distribute_portfolio_briefing,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_portfolio_briefing_schedule_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS portfolio_briefing_schedules (
                id SERIAL PRIMARY KEY,
                schedule_name VARCHAR(255) NOT NULL,
                briefing_type VARCHAR(100) NOT NULL DEFAULT 'board_portfolio',
                audience VARCHAR(100) NOT NULL DEFAULT 'board',
                period_label VARCHAR(255) NOT NULL,
                delivery_channel VARCHAR(50) NOT NULL DEFAULT 'internal',
                delivery_target TEXT NOT NULL DEFAULT 'executive-board',
                message TEXT NOT NULL DEFAULT 'Portfolio board briefing package is ready for review.',
                is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                run_count INTEGER NOT NULL DEFAULT 0,
                last_run_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    db.commit()


def create_portfolio_briefing_schedule(
    db: Session,
    schedule_name: str,
    briefing_type: str,
    audience: str,
    period_label: str,
    delivery_channel: str,
    delivery_target: str,
    message: str,
    is_enabled: bool = True,
) -> dict[str, Any]:
    ensure_portfolio_briefing_schedule_table(db)

    row = db.execute(
        text(
            """
            INSERT INTO portfolio_briefing_schedules (
                schedule_name,
                briefing_type,
                audience,
                period_label,
                delivery_channel,
                delivery_target,
                message,
                is_enabled
            )
            VALUES (
                :schedule_name,
                :briefing_type,
                :audience,
                :period_label,
                :delivery_channel,
                :delivery_target,
                :message,
                :is_enabled
            )
            RETURNING *
            """
        ),
        {
            "schedule_name": schedule_name,
            "briefing_type": briefing_type,
            "audience": audience,
            "period_label": period_label,
            "delivery_channel": delivery_channel,
            "delivery_target": delivery_target,
            "message": message,
            "is_enabled": is_enabled,
        },
    ).mappings().first()

    db.commit()
    return dict(row)


def list_portfolio_briefing_schedules(db: Session) -> list[dict[str, Any]]:
    ensure_portfolio_briefing_schedule_table(db)

    rows = db.execute(
        text(
            """
            SELECT *
            FROM portfolio_briefing_schedules
            ORDER BY created_at DESC, id DESC
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


def get_portfolio_briefing_schedule(db: Session, schedule_id: int) -> dict[str, Any] | None:
    ensure_portfolio_briefing_schedule_table(db)

    row = db.execute(
        text(
            """
            SELECT *
            FROM portfolio_briefing_schedules
            WHERE id = :schedule_id
            """
        ),
        {"schedule_id": schedule_id},
    ).mappings().first()

    return dict(row) if row else None


def _insert_scheduled_briefing(db: Session, schedule: dict[str, Any]) -> dict[str, Any]:
    period_label = schedule["period_label"]

    summary = {
        "tenant_count": 0,
        "status_counts": {},
        "review_count": 0,
        "export_count": 0,
        "scheduled_count": 1,
        "delivery_count": 0,
    }

    next_steps = [
        "Review top-risk accounts with executive leadership.",
        "Stabilize accounts with open governance exceptions and renewal-risk cases.",
        "Increase scheduled QBR coverage for high-priority tenants.",
        "Drive implementation closure for accounts not yet go-live ready.",
        "Use portfolio rollups to prioritize customer success intervention.",
    ]

    row = db.execute(
        text(
            """
            INSERT INTO portfolio_briefings (
                briefing_type,
                audience,
                period_label,
                title,
                executive_summary,
                board_narrative,
                summary_json,
                top_risks_json,
                next_steps_json
            )
            VALUES (
                :briefing_type,
                :audience,
                :period_label,
                :title,
                :executive_summary,
                :board_narrative,
                :summary_json,
                :top_risks_json,
                :next_steps_json
            )
            RETURNING *
            """
        ),
        {
            "briefing_type": schedule["briefing_type"],
            "audience": schedule["audience"],
            "period_label": period_label,
            "title": f"Scheduled Portfolio Board Briefing — {period_label}",
            "executive_summary": (
                f"Scheduled portfolio review for {period_label}. "
                "This package was generated through the LumenAI executive briefing automation workflow."
            ),
            "board_narrative": (
                f"Scheduled board-level portfolio briefing for {period_label}.\n\n"
                "Total tenants: 0.\n"
                "QBR review count: 0.\n"
                "QBR export count: 0.\n"
                "Scheduled QBR jobs: 1.\n"
                "QBR deliveries: 0.\n\n"
                "Top-risk account posture:\n"
                "No top-risk accounts identified.\n\n"
                "Board focus should remain on customer health stabilization, go-live readiness, "
                "governance exception closure, and QBR operating cadence across the portfolio."
            ),
            "summary_json": json.dumps(summary),
            "top_risks_json": json.dumps([]),
            "next_steps_json": json.dumps(next_steps),
        },
    ).mappings().first()

    db.commit()
    return dict(row)


def run_portfolio_briefing_schedule_now(db: Session, schedule_id: int) -> dict[str, Any]:
    schedule = get_portfolio_briefing_schedule(db, schedule_id)

    if not schedule:
        raise ValueError(f"Portfolio briefing schedule {schedule_id} was not found")

    if not schedule.get("is_enabled", True):
        raise ValueError(f"Portfolio briefing schedule {schedule_id} is disabled")

    briefing = _insert_scheduled_briefing(db, schedule)
    export = build_portfolio_briefing_export(db, int(briefing["id"]))

    delivery = distribute_portfolio_briefing(
        db=db,
        briefing_id=int(briefing["id"]),
        export_id=int(export["id"]),
        delivery_channel=str(schedule["delivery_channel"]),
        delivery_target=str(schedule["delivery_target"]),
        message=str(schedule["message"]),
    )

    db.execute(
        text(
            """
            UPDATE portfolio_briefing_schedules
            SET run_count = run_count + 1,
                last_run_at = NOW()
            WHERE id = :schedule_id
            """
        ),
        {"schedule_id": schedule_id},
    )
    db.commit()

    updated_schedule = get_portfolio_briefing_schedule(db, schedule_id)

    return {
        "status": "completed",
        "ran_at": _now_iso(),
        "schedule": updated_schedule,
        "briefing": briefing,
        "export": export,
        "delivery": delivery,
    }
