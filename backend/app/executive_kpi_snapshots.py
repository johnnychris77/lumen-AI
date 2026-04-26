from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_executive_kpi_snapshot_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS executive_kpi_snapshots (
                id SERIAL PRIMARY KEY,
                snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
                snapshot_label VARCHAR(255) NOT NULL DEFAULT '',
                tenant_total INTEGER NOT NULL DEFAULT 0,
                tenant_healthy INTEGER NOT NULL DEFAULT 0,
                tenant_watch INTEGER NOT NULL DEFAULT 0,
                tenant_at_risk INTEGER NOT NULL DEFAULT 0,
                tenant_critical INTEGER NOT NULL DEFAULT 0,
                qbr_overdue INTEGER NOT NULL DEFAULT 0,
                governance_exceptions INTEGER NOT NULL DEFAULT 0,
                remediation_total INTEGER NOT NULL DEFAULT 0,
                remediation_open INTEGER NOT NULL DEFAULT 0,
                remediation_overdue INTEGER NOT NULL DEFAULT 0,
                remediation_escalated INTEGER NOT NULL DEFAULT 0,
                escalation_total INTEGER NOT NULL DEFAULT 0,
                escalation_open INTEGER NOT NULL DEFAULT 0,
                escalation_critical INTEGER NOT NULL DEFAULT 0,
                leadership_decisions_required INTEGER NOT NULL DEFAULT 0,
                delivery_total INTEGER NOT NULL DEFAULT 0,
                delivery_sent INTEGER NOT NULL DEFAULT 0,
                delivery_retry_pending INTEGER NOT NULL DEFAULT 0,
                portfolio_exports INTEGER NOT NULL DEFAULT 0,
                governance_packet_exports INTEGER NOT NULL DEFAULT 0,
                artifact_count INTEGER NOT NULL DEFAULT 0,
                snapshot_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    db.commit()


def _count(db: Session, sql: str) -> int:
    try:
        return int(db.execute(text(sql)).scalar() or 0)
    except Exception:
        return 0


def _artifact_count() -> int:
    from pathlib import Path

    total = 0
    for root in ["generated_portfolio_briefings", "generated_governance_packets"]:
        path = Path(root)
        if path.exists():
            total += len([item for item in path.rglob("*") if item.is_file()])
    return total


def capture_executive_kpi_snapshot(
    db: Session,
    snapshot_label: str = "Executive Operating Metrics Snapshot",
) -> dict[str, Any]:
    ensure_executive_kpi_snapshot_table(db)

    values = {
        "snapshot_label": snapshot_label,
        "tenant_total": _count(db, "SELECT COUNT(*) FROM portfolio_tenants"),
        "tenant_healthy": _count(db, "SELECT COUNT(*) FROM portfolio_tenants WHERE health_status = 'healthy'"),
        "tenant_watch": _count(db, "SELECT COUNT(*) FROM portfolio_tenants WHERE health_status = 'watch'"),
        "tenant_at_risk": _count(db, "SELECT COUNT(*) FROM portfolio_tenants WHERE health_status = 'at_risk'"),
        "tenant_critical": _count(db, "SELECT COUNT(*) FROM portfolio_tenants WHERE health_status = 'critical'"),
        "qbr_overdue": _count(db, "SELECT COUNT(*) FROM portfolio_tenants WHERE next_qbr_date IS NOT NULL AND next_qbr_date < CURRENT_DATE"),
        "governance_exceptions": _count(db, "SELECT COALESCE(SUM(governance_exception_count), 0) FROM portfolio_tenants"),
        "remediation_total": _count(db, "SELECT COUNT(*) FROM tenant_remediations"),
        "remediation_open": _count(db, "SELECT COUNT(*) FROM tenant_remediations WHERE status = 'open'"),
        "remediation_overdue": _count(db, "SELECT COUNT(*) FROM tenant_remediations WHERE due_date IS NOT NULL AND due_date < CURRENT_DATE AND status <> 'closed'"),
        "remediation_escalated": _count(db, "SELECT COUNT(*) FROM tenant_remediations WHERE status = 'escalated'"),
        "escalation_total": _count(db, "SELECT COUNT(*) FROM executive_escalations"),
        "escalation_open": _count(db, "SELECT COUNT(*) FROM executive_escalations WHERE status = 'open'"),
        "escalation_critical": _count(db, "SELECT COUNT(*) FROM executive_escalations WHERE priority = 'critical' AND status <> 'closed'"),
        "leadership_decisions_required": _count(db, "SELECT COUNT(*) FROM executive_escalations WHERE leadership_decision_required = TRUE AND status <> 'closed'"),
        "delivery_total": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_deliveries"),
        "delivery_sent": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_deliveries WHERE status = 'sent'"),
        "delivery_retry_pending": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_deliveries WHERE status = 'retry_pending'"),
        "portfolio_exports": _count(db, "SELECT COUNT(*) FROM portfolio_briefing_exports"),
        "governance_packet_exports": _count(db, "SELECT COUNT(*) FROM executive_governance_packet_exports"),
        "artifact_count": _artifact_count(),
    }

    snapshot_json = {
        "captured_at": _now_iso(),
        "summary": values,
    }

    row = (
        db.execute(
            text(
                """
                INSERT INTO executive_kpi_snapshots (
                    snapshot_label,
                    tenant_total,
                    tenant_healthy,
                    tenant_watch,
                    tenant_at_risk,
                    tenant_critical,
                    qbr_overdue,
                    governance_exceptions,
                    remediation_total,
                    remediation_open,
                    remediation_overdue,
                    remediation_escalated,
                    escalation_total,
                    escalation_open,
                    escalation_critical,
                    leadership_decisions_required,
                    delivery_total,
                    delivery_sent,
                    delivery_retry_pending,
                    portfolio_exports,
                    governance_packet_exports,
                    artifact_count,
                    snapshot_json
                )
                VALUES (
                    :snapshot_label,
                    :tenant_total,
                    :tenant_healthy,
                    :tenant_watch,
                    :tenant_at_risk,
                    :tenant_critical,
                    :qbr_overdue,
                    :governance_exceptions,
                    :remediation_total,
                    :remediation_open,
                    :remediation_overdue,
                    :remediation_escalated,
                    :escalation_total,
                    :escalation_open,
                    :escalation_critical,
                    :leadership_decisions_required,
                    :delivery_total,
                    :delivery_sent,
                    :delivery_retry_pending,
                    :portfolio_exports,
                    :governance_packet_exports,
                    :artifact_count,
                    :snapshot_json
                )
                RETURNING *
                """
            ),
            {**values, "snapshot_json": json.dumps(snapshot_json, default=str)},
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row)


def list_executive_kpi_snapshots(db: Session, limit: int = 30) -> list[dict[str, Any]]:
    ensure_executive_kpi_snapshot_table(db)

    rows = (
        db.execute(
            text(
                """
                SELECT *
                FROM executive_kpi_snapshots
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )

    return [dict(row) for row in rows]


def get_latest_executive_kpi_snapshot(db: Session) -> dict[str, Any] | None:
    snapshots = list_executive_kpi_snapshots(db, limit=1)
    return snapshots[0] if snapshots else None


def executive_kpi_trends(db: Session, limit: int = 12) -> dict[str, Any]:
    ensure_executive_kpi_snapshot_table(db)

    rows = (
        db.execute(
            text(
                """
                SELECT *
                FROM executive_kpi_snapshots
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )

    snapshots = [dict(row) for row in rows]
    chronological = list(reversed(snapshots))

    latest = snapshots[0] if snapshots else None
    previous = snapshots[1] if len(snapshots) > 1 else None

    movement: dict[str, Any] = {}
    fields = [
        "tenant_critical",
        "tenant_at_risk",
        "qbr_overdue",
        "governance_exceptions",
        "remediation_open",
        "remediation_overdue",
        "escalation_open",
        "escalation_critical",
        "leadership_decisions_required",
        "delivery_retry_pending",
        "portfolio_exports",
        "governance_packet_exports",
        "artifact_count",
    ]

    if latest and previous:
        for field in fields:
            movement[field] = {
                "latest": int(latest.get(field) or 0),
                "previous": int(previous.get(field) or 0),
                "delta": int(latest.get(field) or 0) - int(previous.get(field) or 0),
            }

    return {
        "status": "ready",
        "snapshot_count": len(snapshots),
        "latest": latest,
        "previous": previous,
        "movement": movement,
        "series": chronological,
    }
