from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.executive_escalations import ensure_executive_escalation_table


def _today() -> date:
    return datetime.now(timezone.utc).date()


def ensure_executive_decision_table(db: Session) -> None:
    ensure_executive_escalation_table(db)

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS executive_decisions (
                id SERIAL PRIMARY KEY,
                source_type VARCHAR(100) NOT NULL DEFAULT 'manual',
                source_id INTEGER,
                tenant_id INTEGER,
                escalation_id INTEGER,
                packet_id INTEGER,
                decision_title VARCHAR(255) NOT NULL,
                decision_description TEXT NOT NULL DEFAULT '',
                decision_owner VARCHAR(255) NOT NULL DEFAULT '',
                due_date DATE,
                priority VARCHAR(50) NOT NULL DEFAULT 'high',
                status VARCHAR(50) NOT NULL DEFAULT 'proposed',
                leadership_decision_required BOOLEAN NOT NULL DEFAULT TRUE,
                decision_payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMP WITH TIME ZONE
            )
            """
        )
    )
    db.commit()


def create_executive_decision(
    db: Session,
    decision_title: str,
    decision_description: str = "",
    decision_owner: str = "",
    due_date: str | None = None,
    priority: str = "high",
    status: str = "proposed",
    source_type: str = "manual",
    source_id: int | None = None,
    tenant_id: int | None = None,
    escalation_id: int | None = None,
    packet_id: int | None = None,
    leadership_decision_required: bool = True,
    decision_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_executive_decision_table(db)

    row = (
        db.execute(
            text(
                """
                INSERT INTO executive_decisions (
                    source_type,
                    source_id,
                    tenant_id,
                    escalation_id,
                    packet_id,
                    decision_title,
                    decision_description,
                    decision_owner,
                    due_date,
                    priority,
                    status,
                    leadership_decision_required,
                    decision_payload_json,
                    completed_at
                )
                VALUES (
                    :source_type,
                    :source_id,
                    :tenant_id,
                    :escalation_id,
                    :packet_id,
                    :decision_title,
                    :decision_description,
                    :decision_owner,
                    :due_date,
                    :priority,
                    :status,
                    :leadership_decision_required,
                    :decision_payload_json,
                    CASE WHEN :status = 'completed' THEN NOW() ELSE NULL END
                )
                RETURNING *
                """
            ),
            {
                "source_type": source_type,
                "source_id": source_id,
                "tenant_id": tenant_id,
                "escalation_id": escalation_id,
                "packet_id": packet_id,
                "decision_title": decision_title,
                "decision_description": decision_description,
                "decision_owner": decision_owner,
                "due_date": due_date,
                "priority": priority,
                "status": status,
                "leadership_decision_required": leadership_decision_required,
                "decision_payload_json": json.dumps(decision_payload or {}, default=str),
            },
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row)


def _get_escalation(db: Session, escalation_id: int) -> dict[str, Any] | None:
    ensure_executive_decision_table(db)

    row = (
        db.execute(
            text(
                """
                SELECT e.*, t.tenant_name
                FROM executive_escalations e
                LEFT JOIN portfolio_tenants t ON t.id = e.tenant_id
                WHERE e.id = :escalation_id
                """
            ),
            {"escalation_id": escalation_id},
        )
        .mappings()
        .first()
    )

    return dict(row) if row else None


def create_decision_from_escalation(db: Session, escalation_id: int) -> dict[str, Any]:
    escalation = _get_escalation(db, escalation_id)
    if not escalation:
        raise ValueError(f"Executive escalation {escalation_id} was not found")

    due_date = (_today() + timedelta(days=7)).isoformat()
    tenant_name = escalation.get("tenant_name") or "Unassigned tenant"

    return create_executive_decision(
        db=db,
        source_type="executive_escalation",
        source_id=escalation_id,
        tenant_id=escalation.get("tenant_id"),
        escalation_id=escalation_id,
        decision_title=f"Leadership decision required: {tenant_name}",
        decision_description=escalation.get("escalation_summary") or "",
        decision_owner=escalation.get("owner") or "Unassigned",
        due_date=due_date,
        priority=escalation.get("priority") or "high",
        status="proposed",
        leadership_decision_required=True,
        decision_payload=escalation,
    )


def list_executive_decisions(
    db: Session,
    status: str | None = None,
    overdue_only: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_executive_decision_table(db)

    where = []
    params: dict[str, Any] = {"limit": limit}

    if status:
        where.append("d.status = :status")
        params["status"] = status

    if overdue_only:
        where.append("d.due_date IS NOT NULL")
        where.append("d.due_date < CURRENT_DATE")
        where.append("d.status <> 'completed'")

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    rows = (
        db.execute(
            text(
                f"""
                SELECT
                    d.*,
                    t.tenant_name,
                    e.escalation_type,
                    e.escalation_title
                FROM executive_decisions d
                LEFT JOIN portfolio_tenants t ON t.id = d.tenant_id
                LEFT JOIN executive_escalations e ON e.id = d.escalation_id
                {where_sql}
                ORDER BY
                    CASE d.status
                        WHEN 'proposed' THEN 1
                        WHEN 'approved' THEN 2
                        WHEN 'in_progress' THEN 3
                        WHEN 'blocked' THEN 4
                        WHEN 'completed' THEN 5
                        ELSE 6
                    END,
                    CASE d.priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END,
                    d.due_date ASC NULLS LAST,
                    d.id DESC
                LIMIT :limit
                """
            ),
            params,
        )
        .mappings()
        .all()
    )

    return [dict(row) for row in rows]


def get_executive_decision(db: Session, decision_id: int) -> dict[str, Any] | None:
    ensure_executive_decision_table(db)

    row = (
        db.execute(
            text(
                """
                SELECT
                    d.*,
                    t.tenant_name,
                    e.escalation_type,
                    e.escalation_title
                FROM executive_decisions d
                LEFT JOIN portfolio_tenants t ON t.id = d.tenant_id
                LEFT JOIN executive_escalations e ON e.id = d.escalation_id
                WHERE d.id = :decision_id
                """
            ),
            {"decision_id": decision_id},
        )
        .mappings()
        .first()
    )

    return dict(row) if row else None


def update_executive_decision(
    db: Session,
    decision_id: int,
    updates: dict[str, Any],
) -> dict[str, Any] | None:
    ensure_executive_decision_table(db)

    current = get_executive_decision(db, decision_id)
    if not current:
        return None

    allowed = {
        "decision_title",
        "decision_description",
        "decision_owner",
        "due_date",
        "priority",
        "status",
        "leadership_decision_required",
    }

    clean = {key: value for key, value in updates.items() if key in allowed}

    if not clean:
        return current

    set_parts = [f"{key} = :{key}" for key in clean.keys()]
    set_parts.append("updated_at = NOW()")

    if clean.get("status") == "completed":
        set_parts.append("completed_at = COALESCE(completed_at, NOW())")
    elif "status" in clean and clean.get("status") != "completed":
        set_parts.append("completed_at = NULL")

    row = (
        db.execute(
            text(
                f"""
                UPDATE executive_decisions
                SET {", ".join(set_parts)}
                WHERE id = :decision_id
                RETURNING *
                """
            ),
            {**clean, "decision_id": decision_id},
        )
        .mappings()
        .first()
    )

    db.commit()
    return get_executive_decision(db, decision_id) if row else None


def executive_decision_rollup(db: Session) -> dict[str, Any]:
    ensure_executive_decision_table(db)

    def count(sql: str) -> int:
        return int(db.execute(text(sql)).scalar() or 0)

    return {
        "total": count("SELECT COUNT(*) FROM executive_decisions"),
        "proposed": count("SELECT COUNT(*) FROM executive_decisions WHERE status = 'proposed'"),
        "approved": count("SELECT COUNT(*) FROM executive_decisions WHERE status = 'approved'"),
        "in_progress": count("SELECT COUNT(*) FROM executive_decisions WHERE status = 'in_progress'"),
        "blocked": count("SELECT COUNT(*) FROM executive_decisions WHERE status = 'blocked'"),
        "completed": count("SELECT COUNT(*) FROM executive_decisions WHERE status = 'completed'"),
        "overdue": count(
            """
            SELECT COUNT(*)
            FROM executive_decisions
            WHERE due_date IS NOT NULL
              AND due_date < CURRENT_DATE
              AND status <> 'completed'
            """
        ),
        "leadership_required": count(
            """
            SELECT COUNT(*)
            FROM executive_decisions
            WHERE leadership_decision_required = TRUE
              AND status <> 'completed'
            """
        ),
        "critical": count("SELECT COUNT(*) FROM executive_decisions WHERE priority = 'critical' AND status <> 'completed'"),
        "high": count("SELECT COUNT(*) FROM executive_decisions WHERE priority = 'high' AND status <> 'completed'"),
    }


def governance_decision_narrative(db: Session) -> dict[str, Any]:
    rollup = executive_decision_rollup(db)
    open_decisions = [
        item for item in list_executive_decisions(db, limit=25)
        if item.get("status") != "completed"
    ]

    summary = (
        f"There are {rollup['leadership_required']} leadership decision(s) requiring action, "
        f"{rollup['overdue']} overdue decision(s), and {rollup['blocked']} blocked decision(s)."
    )

    recommended_actions = [
        "Review proposed and overdue leadership decisions during the governance cadence.",
        "Assign accountable owners and due dates for decisions without clear ownership.",
        "Close completed decisions to maintain an accurate executive action register.",
    ]

    if rollup["overdue"] > 0:
        recommended_actions.insert(0, "Prioritize overdue executive decisions for immediate review.")

    return {
        "status": "ready",
        "executive_summary": summary,
        "rollup": rollup,
        "open_decisions": open_decisions,
        "recommended_actions": recommended_actions,
    }
