from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


ARTIFACT_ROOT = Path("generated_portfolio_briefings")


def _count(db: Session, sql: str) -> int:
    try:
        value = db.execute(text(sql)).scalar()
        return int(value or 0)
    except Exception:
        return 0


def _rows(db: Session, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        result = db.execute(text(sql), params or {}).mappings().all()
        return [dict(row) for row in result]
    except Exception:
        return []


def _artifact_stats() -> dict[str, Any]:
    files = []
    if ARTIFACT_ROOT.exists():
        files = sorted(str(path) for path in ARTIFACT_ROOT.rglob("*") if path.is_file())

    return {
        "artifact_root": str(ARTIFACT_ROOT),
        "file_count": len(files),
        "recent_files": files[-15:],
    }


def get_executive_briefing_dashboard_summary(db: Session) -> dict[str, Any]:
    summary = {
        "counts": {
            "schedules": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_schedules"),
            "enabled_schedules": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_schedules WHERE is_enabled = TRUE"),
            "briefings": _count(db, "SELECT COUNT(*) FROM portfolio_briefings"),
            "exports": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_exports"),
            "deliveries": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_deliveries"),
            "sent_deliveries": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_deliveries WHERE status = 'sent'"),
            "retry_pending_deliveries": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_deliveries WHERE status = 'retry_pending'"),
            "failed_deliveries": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_deliveries WHERE status = 'failed'"),
        },
        "recent_schedules": _rows(
            db,
            """
            SELECT id, schedule_name, period_label, is_enabled, run_count, last_run_at, created_at
            FROM portfolio_briefing_schedules
            ORDER BY created_at DESC, id DESC
            LIMIT 10
            """,
        ),
        "recent_briefings": _rows(
            db,
            """
            SELECT id, briefing_type, audience, period_label, title, created_at
            FROM portfolio_briefings
            ORDER BY created_at DESC, id DESC
            LIMIT 10
            """,
        ),
        "recent_exports": _rows(
            db,
            """
            SELECT id, briefing_id, export_title, docx_path, pptx_path, pdf_path, created_at
            FROM portfolio_briefing_exports
            ORDER BY created_at DESC, id DESC
            LIMIT 10
            """,
        ),
        "recent_deliveries": _rows(
            db,
            """
            SELECT id, briefing_id, export_id, delivery_channel, delivery_target, status,
                   attempt_count, last_attempt_at, error_message, created_at
            FROM portfolio_briefing_deliveries
            ORDER BY created_at DESC, id DESC
            LIMIT 15
            """,
        ),
        "retry_pending_deliveries": _rows(
            db,
            """
            SELECT id, briefing_id, export_id, delivery_channel, delivery_target, status,
                   attempt_count, last_attempt_at, error_message, created_at
            FROM portfolio_briefing_deliveries
            WHERE status = 'retry_pending'
            ORDER BY created_at DESC, id DESC
            LIMIT 15
            """,
        ),
        "artifacts": _artifact_stats(),
    }

    return summary
