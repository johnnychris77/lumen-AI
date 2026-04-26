from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.tenant_remediations import ensure_tenant_remediation_table, list_tenant_remediations


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_executive_escalation_table(db: Session) -> None:
    ensure_tenant_remediation_table(db)

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS executive_escalations (
                id SERIAL PRIMARY KEY,
                tenant_id INTEGER,
                remediation_id INTEGER,
                escalation_type VARCHAR(100) NOT NULL,
                escalation_title VARCHAR(255) NOT NULL,
                escalation_summary TEXT NOT NULL DEFAULT '',
                leadership_decision_required BOOLEAN NOT NULL DEFAULT TRUE,
                priority VARCHAR(50) NOT NULL DEFAULT 'high',
                status VARCHAR(50) NOT NULL DEFAULT 'open',
                owner VARCHAR(255) NOT NULL DEFAULT '',
                source_payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                acknowledged_at TIMESTAMP WITH TIME ZONE,
                closed_at TIMESTAMP WITH TIME ZONE
            )
            """
        )
    )
    db.commit()


def _existing_open_escalation(
    db: Session,
    remediation_id: int | None,
    escalation_type: str,
) -> bool:
    if remediation_id is None:
        return False

    value = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM executive_escalations
            WHERE remediation_id = :remediation_id
              AND escalation_type = :escalation_type
              AND status IN ('open', 'acknowledged')
            """
        ),
        {
            "remediation_id": remediation_id,
            "escalation_type": escalation_type,
        },
    ).scalar()

    return int(value or 0) > 0


def create_executive_escalation(
    db: Session,
    escalation_type: str,
    escalation_title: str,
    escalation_summary: str,
    tenant_id: int | None = None,
    remediation_id: int | None = None,
    priority: str = "high",
    owner: str = "",
    leadership_decision_required: bool = True,
    source_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_executive_escalation_table(db)

    row = (
        db.execute(
            text(
                """
                INSERT INTO executive_escalations (
                    tenant_id,
                    remediation_id,
                    escalation_type,
                    escalation_title,
                    escalation_summary,
                    leadership_decision_required,
                    priority,
                    status,
                    owner,
                    source_payload_json
                )
                VALUES (
                    :tenant_id,
                    :remediation_id,
                    :escalation_type,
                    :escalation_title,
                    :escalation_summary,
                    :leadership_decision_required,
                    :priority,
                    'open',
                    :owner,
                    :source_payload_json
                )
                RETURNING *
                """
            ),
            {
                "tenant_id": tenant_id,
                "remediation_id": remediation_id,
                "escalation_type": escalation_type,
                "escalation_title": escalation_title,
                "escalation_summary": escalation_summary,
                "leadership_decision_required": leadership_decision_required,
                "priority": priority,
                "owner": owner,
                "source_payload_json": json.dumps(source_payload or {}, default=str),
            },
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row)


def run_executive_escalation_scan(db: Session) -> dict[str, Any]:
    ensure_executive_escalation_table(db)

    created: list[dict[str, Any]] = []

    overdue = list_tenant_remediations(db, overdue_only=True, limit=100)
    for item in overdue:
        remediation_id = int(item["id"])
        if _existing_open_escalation(db, remediation_id, "overdue_remediation"):
            continue

        created.append(
            create_executive_escalation(
                db=db,
                tenant_id=item.get("tenant_id"),
                remediation_id=remediation_id,
                escalation_type="overdue_remediation",
                escalation_title=f"Overdue remediation: {item.get('tenant_name') or 'Tenant'}",
                escalation_summary=(
                    f"Remediation action '{item.get('action_title')}' is overdue. "
                    f"Owner: {item.get('owner') or 'Unassigned'}. "
                    f"Due date: {item.get('due_date') or 'not set'}. "
                    f"Priority: {item.get('priority')}."
                ),
                priority="critical" if item.get("priority") == "critical" else "high",
                owner=item.get("owner") or item.get("customer_success_owner") or "Unassigned",
                leadership_decision_required=True,
                source_payload=dict(item),
            )
        )

    blocked = list_tenant_remediations(db, status="blocked", limit=100)
    for item in blocked:
        remediation_id = int(item["id"])
        if _existing_open_escalation(db, remediation_id, "blocked_remediation"):
            continue

        created.append(
            create_executive_escalation(
                db=db,
                tenant_id=item.get("tenant_id"),
                remediation_id=remediation_id,
                escalation_type="blocked_remediation",
                escalation_title=f"Blocked remediation: {item.get('tenant_name') or 'Tenant'}",
                escalation_summary=(
                    f"Remediation action '{item.get('action_title')}' is blocked and requires leadership unblock. "
                    f"Owner: {item.get('owner') or 'Unassigned'}."
                ),
                priority="high",
                owner=item.get("owner") or "Unassigned",
                leadership_decision_required=True,
                source_payload=dict(item),
            )
        )

    escalated = list_tenant_remediations(db, status="escalated", limit=100)
    for item in escalated:
        remediation_id = int(item["id"])
        if _existing_open_escalation(db, remediation_id, "escalated_remediation"):
            continue

        created.append(
            create_executive_escalation(
                db=db,
                tenant_id=item.get("tenant_id"),
                remediation_id=remediation_id,
                escalation_type="escalated_remediation",
                escalation_title=f"Escalated remediation: {item.get('tenant_name') or 'Tenant'}",
                escalation_summary=(
                    f"Remediation action '{item.get('action_title')}' has been escalated. "
                    f"Executive review is required to confirm decision, owner, and due date."
                ),
                priority=item.get("priority") or "high",
                owner=item.get("owner") or "Unassigned",
                leadership_decision_required=True,
                source_payload=dict(item),
            )
        )

    critical_open = [
        item
        for item in list_tenant_remediations(db, limit=100)
        if item.get("priority") == "critical" and item.get("status") != "closed"
    ]

    for item in critical_open:
        remediation_id = int(item["id"])
        if _existing_open_escalation(db, remediation_id, "critical_priority_remediation"):
            continue

        created.append(
            create_executive_escalation(
                db=db,
                tenant_id=item.get("tenant_id"),
                remediation_id=remediation_id,
                escalation_type="critical_priority_remediation",
                escalation_title=f"Critical priority remediation: {item.get('tenant_name') or 'Tenant'}",
                escalation_summary=(
                    f"Critical remediation action '{item.get('action_title')}' requires executive cadence review. "
                    f"Owner: {item.get('owner') or 'Unassigned'}."
                ),
                priority="critical",
                owner=item.get("owner") or "Unassigned",
                leadership_decision_required=True,
                source_payload=dict(item),
            )
        )

    return {
        "status": "completed",
        "scanned_at": _now_iso(),
        "created_count": len(created),
        "created": created,
    }


def list_executive_escalations(
    db: Session,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    ensure_executive_escalation_table(db)

    if status:
        rows = (
            db.execute(
                text(
                    """
                    SELECT e.*, t.tenant_name
                    FROM executive_escalations e
                    LEFT JOIN portfolio_tenants t ON t.id = e.tenant_id
                    WHERE e.status = :status
                    ORDER BY
                        CASE e.priority
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                            ELSE 5
                        END,
                        e.created_at DESC,
                        e.id DESC
                    LIMIT :limit
                    """
                ),
                {"status": status, "limit": limit},
            )
            .mappings()
            .all()
        )
    else:
        rows = (
            db.execute(
                text(
                    """
                    SELECT e.*, t.tenant_name
                    FROM executive_escalations e
                    LEFT JOIN portfolio_tenants t ON t.id = e.tenant_id
                    ORDER BY
                        CASE e.status
                            WHEN 'open' THEN 1
                            WHEN 'acknowledged' THEN 2
                            WHEN 'closed' THEN 3
                            ELSE 4
                        END,
                        CASE e.priority
                            WHEN 'critical' THEN 1
                            WHEN 'high' THEN 2
                            WHEN 'medium' THEN 3
                            WHEN 'low' THEN 4
                            ELSE 5
                        END,
                        e.created_at DESC,
                        e.id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            .mappings()
            .all()
        )

    return [dict(row) for row in rows]


def update_executive_escalation_status(
    db: Session,
    escalation_id: int,
    status: str,
) -> dict[str, Any] | None:
    ensure_executive_escalation_table(db)

    if status == "acknowledged":
        set_extra = "acknowledged_at = COALESCE(acknowledged_at, NOW()), closed_at = NULL"
    elif status == "closed":
        set_extra = "closed_at = COALESCE(closed_at, NOW())"
    else:
        set_extra = "acknowledged_at = NULL, closed_at = NULL"

    row = (
        db.execute(
            text(
                f"""
                UPDATE executive_escalations
                SET status = :status,
                    {set_extra}
                WHERE id = :escalation_id
                RETURNING *
                """
            ),
            {
                "status": status,
                "escalation_id": escalation_id,
            },
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row) if row else None


def executive_escalation_rollup(db: Session) -> dict[str, Any]:
    ensure_executive_escalation_table(db)

    def count(sql: str) -> int:
        return int(db.execute(text(sql)).scalar() or 0)

    return {
        "total": count("SELECT COUNT(*) FROM executive_escalations"),
        "open": count("SELECT COUNT(*) FROM executive_escalations WHERE status = 'open'"),
        "acknowledged": count("SELECT COUNT(*) FROM executive_escalations WHERE status = 'acknowledged'"),
        "closed": count("SELECT COUNT(*) FROM executive_escalations WHERE status = 'closed'"),
        "critical": count("SELECT COUNT(*) FROM executive_escalations WHERE priority = 'critical' AND status <> 'closed'"),
        "high": count("SELECT COUNT(*) FROM executive_escalations WHERE priority = 'high' AND status <> 'closed'"),
        "leadership_decision_required": count(
            """
            SELECT COUNT(*)
            FROM executive_escalations
            WHERE leadership_decision_required = TRUE
              AND status <> 'closed'
            """
        ),
    }


def generate_governance_packet(db: Session) -> dict[str, Any]:
    ensure_executive_escalation_table(db)

    open_items = list_executive_escalations(db, status="open", limit=50)
    acknowledged = list_executive_escalations(db, status="acknowledged", limit=50)
    rollup = executive_escalation_rollup(db)

    top_lines = []
    for item in open_items[:10]:
        top_lines.append(
            {
                "tenant": item.get("tenant_name") or "Unassigned tenant",
                "priority": item.get("priority"),
                "type": item.get("escalation_type"),
                "summary": item.get("escalation_summary"),
                "owner": item.get("owner") or "Unassigned",
                "leadership_decision_required": item.get("leadership_decision_required"),
            }
        )

    recommended_decisions = [
        "Confirm executive owner for each open critical escalation.",
        "Resolve blocked remediation actions or assign leadership unblock owner.",
        "Review overdue remediation actions and reset due dates with accountable owners.",
        "Close governance exceptions tied to critical and high-priority tenant risk.",
        "Document decisions from governance cadence and track closure by next review.",
    ]

    narrative = (
        "Executive governance packet generated from active escalations. "
        f"There are {rollup['open']} open escalation(s), {rollup['critical']} critical item(s), "
        f"and {rollup['leadership_decision_required']} item(s) requiring leadership decision."
    )

    return {
        "status": "generated",
        "generated_at": _now_iso(),
        "rollup": rollup,
        "executive_summary": narrative,
        "open_escalations": open_items,
        "acknowledged_escalations": acknowledged,
        "top_governance_items": top_lines,
        "recommended_leadership_decisions": recommended_decisions,
    }
