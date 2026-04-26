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


    summary["portfolio_tenants"] = {
        "total": _count(db, "SELECT COUNT(*) FROM portfolio_tenants"),
        "healthy": _count(db, "SELECT COUNT(*) FROM portfolio_tenants WHERE health_status = 'healthy'"),
        "watch": _count(db, "SELECT COUNT(*) FROM portfolio_tenants WHERE health_status = 'watch'"),
        "at_risk": _count(db, "SELECT COUNT(*) FROM portfolio_tenants WHERE health_status = 'at_risk'"),
        "critical": _count(db, "SELECT COUNT(*) FROM portfolio_tenants WHERE health_status = 'critical'"),
        "qbr_overdue": _count(db, "SELECT COUNT(*) FROM portfolio_tenants WHERE next_qbr_date IS NOT NULL AND next_qbr_date < CURRENT_DATE"),
        "governance_exceptions": _count(db, "SELECT COALESCE(SUM(governance_exception_count), 0) FROM portfolio_tenants"),
    }

    summary["top_risk_tenants"] = _rows(
        db,
        '''
        SELECT id, tenant_name, health_status, health_score, renewal_risk,
               implementation_risk, governance_exception_count, next_qbr_date,
               executive_owner, customer_success_owner
        FROM portfolio_tenants
        ORDER BY health_score ASC, governance_exception_count DESC, id DESC
        LIMIT 10
        '''
    )


    try:
        from app.tenant_insights import portfolio_insight_rollup, get_top_risk_tenant_insights
        summary["tenant_insights"] = portfolio_insight_rollup(db)
        summary["top_tenant_insights"] = get_top_risk_tenant_insights(db, limit=10)
    except Exception:
        summary["tenant_insights"] = {
            "tenant_insight_count": 0,
            "board_attention_count": 0,
            "critical_count": 0,
            "high_or_moderate_count": 0,
            "top_board_attention_items": [],
            "executive_focus_summary": "Tenant insights unavailable."
        }
        summary["top_tenant_insights"] = []


    try:
        from app.tenant_remediations import remediation_rollup, list_tenant_remediations
        summary["tenant_remediations"] = remediation_rollup(db)
        summary["open_remediations"] = list_tenant_remediations(db, status="open", limit=15)
        summary["overdue_remediations"] = list_tenant_remediations(db, overdue_only=True, limit=15)
    except Exception:
        summary["tenant_remediations"] = {
            "total": 0,
            "open": 0,
            "in_progress": 0,
            "blocked": 0,
            "escalated": 0,
            "closed": 0,
            "overdue": 0,
            "critical_priority": 0,
            "high_priority": 0,
        }
        summary["open_remediations"] = []
        summary["overdue_remediations"] = []

    return summary
