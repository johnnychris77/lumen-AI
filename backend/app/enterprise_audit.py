from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_enterprise_audit_table(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS enterprise_audit_events (
                id SERIAL PRIMARY KEY,
                actor VARCHAR(255) NOT NULL DEFAULT 'unknown',
                actor_role VARCHAR(100) NOT NULL DEFAULT 'unknown',
                event_type VARCHAR(100) NOT NULL DEFAULT 'api_request',
                resource_type VARCHAR(100) NOT NULL DEFAULT '',
                resource_id VARCHAR(100) NOT NULL DEFAULT '',
                action VARCHAR(100) NOT NULL DEFAULT '',
                method VARCHAR(20) NOT NULL DEFAULT '',
                path TEXT NOT NULL DEFAULT '',
                status_code INTEGER,
                success BOOLEAN NOT NULL DEFAULT TRUE,
                client_host VARCHAR(255) NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '',
                event_payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    db.commit()


def create_audit_event(
    db: Session,
    actor: str = "unknown",
    actor_role: str = "unknown",
    event_type: str = "api_request",
    resource_type: str = "",
    resource_id: str = "",
    action: str = "",
    method: str = "",
    path: str = "",
    status_code: int | None = None,
    success: bool = True,
    client_host: str = "",
    user_agent: str = "",
    event_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_enterprise_audit_table(db)

    row = (
        db.execute(
            text(
                """
                INSERT INTO enterprise_audit_events (
                    actor,
                    actor_role,
                    event_type,
                    resource_type,
                    resource_id,
                    action,
                    method,
                    path,
                    status_code,
                    success,
                    client_host,
                    user_agent,
                    event_payload_json
                )
                VALUES (
                    :actor,
                    :actor_role,
                    :event_type,
                    :resource_type,
                    :resource_id,
                    :action,
                    :method,
                    :path,
                    :status_code,
                    :success,
                    :client_host,
                    :user_agent,
                    :event_payload_json
                )
                RETURNING *
                """
            ),
            {
                "actor": actor,
                "actor_role": actor_role,
                "event_type": event_type,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "method": method,
                "path": path,
                "status_code": status_code,
                "success": success,
                "client_host": client_host,
                "user_agent": user_agent,
                "event_payload_json": json.dumps(event_payload or {}, default=str),
            },
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row)


def infer_resource_type(path: str) -> str:
    if "portfolio-tenants" in path:
        return "portfolio_tenant"
    if "tenant-insights" in path:
        return "tenant_insight"
    if "tenant-remediations" in path:
        return "tenant_remediation"
    if "executive-escalations" in path:
        return "executive_escalation"
    if "executive-decisions" in path:
        return "executive_decision"
    if "governance-packets" in path:
        return "governance_packet"
    if "executive-kpi" in path:
        return "executive_kpi"
    if "portfolio-briefings" in path:
        return "portfolio_briefing"
    if "executive-briefing-dashboard" in path:
        return "executive_dashboard"
    return "api"


def infer_action(method: str, path: str) -> str:
    method = method.upper()

    if method == "GET":
        return "read"
    if method == "POST" and any(word in path for word in ["run", "capture", "generate", "start"]):
        return "execute"
    if method == "POST":
        return "create"
    if method in {"PATCH", "PUT"}:
        return "update"
    if method == "DELETE":
        return "delete"

    return method.lower()


def list_audit_events(db: Session, limit: int = 100) -> list[dict[str, Any]]:
    ensure_enterprise_audit_table(db)

    rows = (
        db.execute(
            text(
                """
                SELECT *
                FROM enterprise_audit_events
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


def audit_rollup(db: Session) -> dict[str, Any]:
    ensure_enterprise_audit_table(db)

    def count(sql: str) -> int:
        return int(db.execute(text(sql)).scalar() or 0)

    by_resource = (
        db.execute(
            text(
                """
                SELECT resource_type, COUNT(*) AS count
                FROM enterprise_audit_events
                GROUP BY resource_type
                ORDER BY count DESC
                LIMIT 12
                """
            )
        )
        .mappings()
        .all()
    )

    by_action = (
        db.execute(
            text(
                """
                SELECT action, COUNT(*) AS count
                FROM enterprise_audit_events
                GROUP BY action
                ORDER BY count DESC
                LIMIT 12
                """
            )
        )
        .mappings()
        .all()
    )

    return {
        "total": count("SELECT COUNT(*) FROM enterprise_audit_events"),
        "success": count("SELECT COUNT(*) FROM enterprise_audit_events WHERE success = TRUE"),
        "failed": count("SELECT COUNT(*) FROM enterprise_audit_events WHERE success = FALSE"),
        "writes": count("SELECT COUNT(*) FROM enterprise_audit_events WHERE action IN ('create', 'update', 'delete', 'execute')"),
        "reads": count("SELECT COUNT(*) FROM enterprise_audit_events WHERE action = 'read'"),
        "dashboard_views": count("SELECT COUNT(*) FROM enterprise_audit_events WHERE resource_type = 'executive_dashboard'"),
        "decision_events": count("SELECT COUNT(*) FROM enterprise_audit_events WHERE resource_type = 'executive_decision'"),
        "governance_events": count("SELECT COUNT(*) FROM enterprise_audit_events WHERE resource_type = 'governance_packet'"),
        "by_resource": [dict(row) for row in by_resource],
        "by_action": [dict(row) for row in by_action],
    }


def compliance_narrative(db: Session) -> dict[str, Any]:
    rollup = audit_rollup(db)

    summary = (
        f"Enterprise audit trail contains {rollup['total']} event(s), "
        f"including {rollup['writes']} write/execute event(s), "
        f"{rollup['reads']} read event(s), and {rollup['failed']} failed event(s)."
    )

    recommended_actions = [
        "Review failed audit events during administrative governance review.",
        "Monitor write/execute actions for executive decision, remediation, escalation, and packet workflows.",
        "Use audit event history to support compliance review, operational transparency, and accountability.",
    ]

    if rollup["failed"] > 0:
        recommended_actions.insert(0, "Investigate failed API events and confirm whether retry or access correction is required.")

    return {
        "status": "ready",
        "executive_summary": summary,
        "rollup": rollup,
        "recommended_actions": recommended_actions,
    }
