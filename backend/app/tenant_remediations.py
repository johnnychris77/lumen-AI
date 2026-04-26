from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.portfolio_tenants import ensure_portfolio_tenant_table, get_portfolio_tenant
from app.tenant_insights import get_tenant_insight


def _today() -> date:
    return datetime.now(timezone.utc).date()


def ensure_tenant_remediation_table(db: Session) -> None:
    ensure_portfolio_tenant_table(db)

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tenant_remediations (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER NOT NULL,
                risk_source VARCHAR(255) NOT NULL DEFAULT 'manual',
                action_title VARCHAR(255) NOT NULL,
                action_description TEXT NOT NULL DEFAULT '',
                owner VARCHAR(255) NOT NULL DEFAULT '',
                due_date DATE,
                priority VARCHAR(50) NOT NULL DEFAULT 'medium',
                status VARCHAR(50) NOT NULL DEFAULT 'open',
                escalation_level INTEGER NOT NULL DEFAULT 0,
                source_insight_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                closed_at TIMESTAMP WITH TIME ZONE
            )
            """
        )
    )
    db.commit()


def create_tenant_remediation(
    db: Session,
    tenant_id: int,
    action_title: str,
    action_description: str = "",
    owner: str = "",
    due_date: str | None = None,
    priority: str = "medium",
    status: str = "open",
    escalation_level: int = 0,
    risk_source: str = "manual",
    source_insight_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_tenant_remediation_table(db)

    tenant = get_portfolio_tenant(db, tenant_id)
    if not tenant:
        raise ValueError(f"Portfolio tenant {tenant_id} was not found")

    row = (
        db.execute(
            text(
                """
                INSERT INTO tenant_remediations (
                    tenant_id,
                    risk_source,
                    action_title,
                    action_description,
                    owner,
                    due_date,
                    priority,
                    status,
                    escalation_level,
                    source_insight_json,
                    closed_at
                )
                VALUES (
                    :tenant_id,
                    :risk_source,
                    :action_title,
                    :action_description,
                    :owner,
                    :due_date,
                    :priority,
                    :status,
                    :escalation_level,
                    :source_insight_json,
                    CASE WHEN :status = 'closed' THEN NOW() ELSE NULL END
                )
                RETURNING *
                """
            ),
            {
                "tenant_id": tenant_id,
                "risk_source": risk_source,
                "action_title": action_title,
                "action_description": action_description,
                "owner": owner,
                "due_date": due_date,
                "priority": priority,
                "status": status,
                "escalation_level": escalation_level,
                "source_insight_json": json.dumps(source_insight_json or {}, default=str),
            },
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row)


def list_tenant_remediations(
    db: Session,
    status: str | None = None,
    tenant_id: int | None = None,
    overdue_only: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_tenant_remediation_table(db)

    where = []
    params: dict[str, Any] = {"limit": limit}

    if status:
        where.append("r.status = :status")
        params["status"] = status

    if tenant_id:
        where.append("r.tenant_id = :tenant_id")
        params["tenant_id"] = tenant_id

    if overdue_only:
        where.append("r.due_date IS NOT NULL")
        where.append("r.due_date < CURRENT_DATE")
        where.append("r.status <> 'closed'")

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    rows = (
        db.execute(
            text(
                f"""
                SELECT
                    r.*,
                    t.tenant_name,
                    t.health_status,
                    t.health_score,
                    t.customer_success_owner,
                    t.executive_owner
                FROM tenant_remediations r
                LEFT JOIN portfolio_tenants t ON t.id = r.tenant_id
                {where_sql}
                ORDER BY
                    CASE r.priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END,
                    r.due_date ASC NULLS LAST,
                    r.id DESC
                LIMIT :limit
                """
            ),
            params,
        )
        .mappings()
        .all()
    )

    return [dict(row) for row in rows]


def get_tenant_remediation(db: Session, remediation_id: int) -> dict[str, Any] | None:
    ensure_tenant_remediation_table(db)

    row = (
        db.execute(
            text(
                """
                SELECT
                    r.*,
                    t.tenant_name,
                    t.health_status,
                    t.health_score,
                    t.customer_success_owner,
                    t.executive_owner
                FROM tenant_remediations r
                LEFT JOIN portfolio_tenants t ON t.id = r.tenant_id
                WHERE r.id = :remediation_id
                """
            ),
            {"remediation_id": remediation_id},
        )
        .mappings()
        .first()
    )

    return dict(row) if row else None


def update_tenant_remediation(
    db: Session,
    remediation_id: int,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    ensure_tenant_remediation_table(db)

    current = get_tenant_remediation(db, remediation_id)
    if not current:
        return None

    allowed = {
        "action_title",
        "action_description",
        "owner",
        "due_date",
        "priority",
        "status",
        "escalation_level",
        "risk_source",
    }

    clean = {key: value for key, value in updates.items() if key in allowed}

    if not clean:
        return current

    set_parts = [f"{key} = :{key}" for key in clean.keys()]
    set_parts.append("updated_at = NOW()")

    if clean.get("status") == "closed":
        set_parts.append("closed_at = COALESCE(closed_at, NOW())")
    elif "status" in clean and clean.get("status") != "closed":
        set_parts.append("closed_at = NULL")

    params = {**clean, "remediation_id": remediation_id}

    row = (
        db.execute(
            text(
                f"""
                UPDATE tenant_remediations
                SET {", ".join(set_parts)}
                WHERE id = :remediation_id
                RETURNING *
                """
            ),
            params,
        )
        .mappings()
        .first()
    )

    db.commit()
    return get_tenant_remediation(db, remediation_id) if row else None


def create_remediations_from_tenant_insight(db: Session, tenant_id: int) -> list[dict[str, Any]]:
    ensure_tenant_remediation_table(db)

    insight = get_tenant_insight(db, tenant_id)
    if not insight:
        raise ValueError(f"Tenant insight for tenant {tenant_id} was not found")

    tenant = get_portfolio_tenant(db, tenant_id)
    if not tenant:
        raise ValueError(f"Portfolio tenant {tenant_id} was not found")

    owner = (
        tenant.get("customer_success_owner")
        or tenant.get("executive_owner")
        or "Unassigned"
    )

    due_days = 7 if insight.get("board_attention_required") else 30
    due_date = (_today() + timedelta(days=due_days)).isoformat()

    priority = "critical" if insight.get("risk_level") == "critical" else (
        "high" if insight.get("board_attention_required") else "medium"
    )

    created: list[dict[str, Any]] = []

    for action in insight.get("recommended_actions", []):
        created.append(
            create_tenant_remediation(
                db=db,
                tenant_id=tenant_id,
                risk_source="tenant_insight",
                action_title=str(action)[:255],
                action_description=insight.get("executive_summary", ""),
                owner=owner,
                due_date=due_date,
                priority=priority,
                status="open",
                escalation_level=1 if insight.get("board_attention_required") else 0,
                source_insight_json=insight,
            )
        )

    return created


def remediation_rollup(db: Session) -> dict[str, Any]:
    ensure_tenant_remediation_table(db)

    def count(sql: str) -> int:
        return int(db.execute(text(sql)).scalar() or 0)

    return {
        "total": count("SELECT COUNT(*) FROM tenant_remediations"),
        "open": count("SELECT COUNT(*) FROM tenant_remediations WHERE status = 'open'"),
        "in_progress": count("SELECT COUNT(*) FROM tenant_remediations WHERE status = 'in_progress'"),
        "blocked": count("SELECT COUNT(*) FROM tenant_remediations WHERE status = 'blocked'"),
        "escalated": count("SELECT COUNT(*) FROM tenant_remediations WHERE status = 'escalated'"),
        "closed": count("SELECT COUNT(*) FROM tenant_remediations WHERE status = 'closed'"),
        "overdue": count(
            """
            SELECT COUNT(*)
            FROM tenant_remediations
            WHERE due_date IS NOT NULL
              AND due_date < CURRENT_DATE
              AND status <> 'closed'
            """
        ),
        "critical_priority": count("SELECT COUNT(*) FROM tenant_remediations WHERE priority = 'critical' AND status <> 'closed'"),
        "high_priority": count("SELECT COUNT(*) FROM tenant_remediations WHERE priority = 'high' AND status <> 'closed'"),
    }
