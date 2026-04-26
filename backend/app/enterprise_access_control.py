from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


ROLE_ORDER = {
    "viewer": 1,
    "auditor": 2,
    "operator": 3,
    "executive": 4,
    "admin": 5,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_enterprise_access_tables(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS enterprise_access_decisions (
                id SERIAL PRIMARY KEY,
                actor VARCHAR(255) NOT NULL DEFAULT 'unknown',
                actor_role VARCHAR(100) NOT NULL DEFAULT 'unknown',
                resource_type VARCHAR(100) NOT NULL DEFAULT '',
                action VARCHAR(100) NOT NULL DEFAULT '',
                method VARCHAR(20) NOT NULL DEFAULT '',
                path TEXT NOT NULL DEFAULT '',
                allowed BOOLEAN NOT NULL DEFAULT TRUE,
                reason TEXT NOT NULL DEFAULT '',
                policy_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
            """
        )
    )

    db.commit()


def infer_actor_and_role(headers: dict[str, str]) -> tuple[str, str]:
    authorization = headers.get("authorization", "")
    explicit_role = headers.get("x-lumenai-role", "").strip().lower()
    explicit_actor = headers.get("x-lumenai-actor", "").strip()

    if "dev-token" in authorization:
        return explicit_actor or "dev-user", explicit_role or "admin"

    return explicit_actor or "unknown", explicit_role or "viewer"


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
    if "enterprise-audit" in path:
        return "enterprise_audit"
    if "enterprise-access" in path:
        return "enterprise_access"
    if "portfolio-briefings" in path:
        return "portfolio_briefing"
    if "executive-briefing-dashboard" in path:
        return "executive_dashboard"
    return "api"


def infer_action(method: str, path: str) -> str:
    method = method.upper()

    if method == "GET":
        return "read"

    if method == "POST" and any(word in path for word in ["run", "capture", "generate", "start", "retry"]):
        return "execute"

    if method == "POST":
        return "create"

    if method in {"PATCH", "PUT"}:
        return "update"

    if method == "DELETE":
        return "delete"

    return method.lower()


def required_role_for(resource_type: str, action: str) -> str:
    if action == "read":
        if resource_type in {"enterprise_audit", "enterprise_access"}:
            return "auditor"
        return "viewer"

    if resource_type in {"enterprise_audit", "enterprise_access"}:
        return "admin"

    if resource_type in {"executive_decision", "executive_escalation", "governance_packet"}:
        return "executive"

    if resource_type in {"tenant_remediation", "portfolio_tenant", "portfolio_briefing", "executive_kpi"}:
        return "operator"

    return "operator"


def evaluate_access(actor_role: str, resource_type: str, action: str) -> dict[str, Any]:
    actor_role = (actor_role or "viewer").lower()
    required = required_role_for(resource_type, action)

    actor_rank = ROLE_ORDER.get(actor_role, 0)
    required_rank = ROLE_ORDER.get(required, 99)
    allowed = actor_rank >= required_rank

    reason = (
        f"Allowed: role '{actor_role}' meets required role '{required}'."
        if allowed
        else f"Denied: role '{actor_role}' does not meet required role '{required}'."
    )

    return {
        "allowed": allowed,
        "actor_role": actor_role,
        "required_role": required,
        "resource_type": resource_type,
        "action": action,
        "reason": reason,
    }


def record_access_decision(
    db: Session,
    actor: str,
    actor_role: str,
    resource_type: str,
    action: str,
    method: str,
    path: str,
    allowed: bool,
    reason: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_enterprise_access_tables(db)

    row = (
        db.execute(
            text(
                """
                INSERT INTO enterprise_access_decisions (
                    actor,
                    actor_role,
                    resource_type,
                    action,
                    method,
                    path,
                    allowed,
                    reason,
                    policy_json
                )
                VALUES (
                    :actor,
                    :actor_role,
                    :resource_type,
                    :action,
                    :method,
                    :path,
                    :allowed,
                    :reason,
                    :policy_json
                )
                RETURNING *
                """
            ),
            {
                "actor": actor,
                "actor_role": actor_role,
                "resource_type": resource_type,
                "action": action,
                "method": method,
                "path": path,
                "allowed": allowed,
                "reason": reason,
                "policy_json": json.dumps(policy or {}, default=str),
            },
        )
        .mappings()
        .first()
    )

    db.commit()
    return dict(row)


def list_access_decisions(db: Session, limit: int = 100) -> list[dict[str, Any]]:
    ensure_enterprise_access_tables(db)

    rows = (
        db.execute(
            text(
                """
                SELECT *
                FROM enterprise_access_decisions
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


def access_rollup(db: Session) -> dict[str, Any]:
    ensure_enterprise_access_tables(db)

    def count(sql: str) -> int:
        return int(db.execute(text(sql)).scalar() or 0)

    by_role = (
        db.execute(
            text(
                """
                SELECT actor_role, COUNT(*) AS count
                FROM enterprise_access_decisions
                GROUP BY actor_role
                ORDER BY count DESC
                LIMIT 12
                """
            )
        )
        .mappings()
        .all()
    )

    by_resource = (
        db.execute(
            text(
                """
                SELECT resource_type, COUNT(*) AS count
                FROM enterprise_access_decisions
                GROUP BY resource_type
                ORDER BY count DESC
                LIMIT 12
                """
            )
        )
        .mappings()
        .all()
    )

    return {
        "total": count("SELECT COUNT(*) FROM enterprise_access_decisions"),
        "allowed": count("SELECT COUNT(*) FROM enterprise_access_decisions WHERE allowed = TRUE"),
        "denied": count("SELECT COUNT(*) FROM enterprise_access_decisions WHERE allowed = FALSE"),
        "admin_events": count("SELECT COUNT(*) FROM enterprise_access_decisions WHERE actor_role = 'admin'"),
        "executive_events": count("SELECT COUNT(*) FROM enterprise_access_decisions WHERE actor_role = 'executive'"),
        "operator_events": count("SELECT COUNT(*) FROM enterprise_access_decisions WHERE actor_role = 'operator'"),
        "viewer_events": count("SELECT COUNT(*) FROM enterprise_access_decisions WHERE actor_role = 'viewer'"),
        "by_role": [dict(row) for row in by_role],
        "by_resource": [dict(row) for row in by_resource],
    }


def access_governance_narrative(db: Session) -> dict[str, Any]:
    rollup = access_rollup(db)

    summary = (
        f"Enterprise access control has recorded {rollup['total']} access decision(s), "
        f"including {rollup['allowed']} allowed and {rollup['denied']} denied request(s)."
    )

    recommended_actions = [
        "Review denied access decisions to confirm expected role enforcement.",
        "Monitor admin and executive write/execute activity for governance-sensitive workflows.",
        "Use X-LumenAI-Role headers during testing to validate viewer, auditor, operator, executive, and admin boundaries.",
    ]

    if rollup["denied"] > 0:
        recommended_actions.insert(0, "Investigate denied access decisions for possible training, role assignment, or policy tuning.")

    return {
        "status": "ready",
        "executive_summary": summary,
        "rollup": rollup,
        "recommended_actions": recommended_actions,
    }


def policy_matrix() -> list[dict[str, Any]]:
    resources = [
        "portfolio_tenant",
        "tenant_remediation",
        "executive_escalation",
        "executive_decision",
        "governance_packet",
        "executive_kpi",
        "enterprise_audit",
        "enterprise_access",
    ]

    actions = ["read", "create", "update", "execute", "delete"]

    return [
        {
            "resource_type": resource,
            "action": action,
            "required_role": required_role_for(resource, action),
        }
        for resource in resources
        for action in actions
    ]
