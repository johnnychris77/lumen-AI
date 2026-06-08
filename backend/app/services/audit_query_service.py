from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def _details(event: AuditLog) -> dict[str, Any]:
    raw = getattr(event, "details", {}) or {}

    if isinstance(raw, dict):
        return raw

    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"raw_details": raw}
        except json.JSONDecodeError:
            return {"raw_details": raw}

    return {"raw_details": str(raw)}


def _matches_detail_filters(
    details: dict[str, Any],
    *,
    tenant_id: str | None = None,
    actor: str | None = None,
    actor_role: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> bool:
    filters = {
        "tenant_id": tenant_id,
        "actor": actor,
        "actor_role": actor_role,
        "request_id": request_id,
        "correlation_id": correlation_id,
    }

    for key, expected in filters.items():
        if expected is None:
            continue

        if str(details.get(key, "")) != str(expected):
            return False

    return True


def serialize_audit_event(event: AuditLog) -> dict[str, Any]:
    details = _details(event)

    return {
        "id": event.id,
        "action_type": getattr(event, "action_type", ""),
        "resource_type": getattr(event, "resource_type", ""),
        "resource_id": getattr(event, "resource_id", ""),
        "actor": details.get("actor") or getattr(event, "actor_email", ""),
        "actor_role": details.get("actor_role") or getattr(event, "actor_role", ""),
        "tenant_id": details.get("tenant_id", ""),
        "tenant_name": details.get("tenant_name", ""),
        "request_id": details.get("request_id", ""),
        "correlation_id": details.get("correlation_id", ""),
        "auth_provider": details.get("auth_provider", ""),
        "issuer": details.get("issuer", ""),
        "event_hash": details.get("event_hash", ""),
        "previous_event_hash": details.get("previous_event_hash", ""),
        "created_at": event.created_at.isoformat() if getattr(event, "created_at", None) else "",
        "details": details,
    }


def query_audit_events(
    db: Session,
    *,
    tenant_id: str | None = None,
    actor: str | None = None,
    actor_role: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    action_type: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    safe_limit = max(1, min(limit, 200))

    query = db.query(AuditLog)

    if action_type:
        query = query.filter(AuditLog.action_type == action_type)

    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    if resource_id:
        query = query.filter(AuditLog.resource_id == str(resource_id))

    events = query.order_by(AuditLog.id.desc()).limit(500).all()

    filtered = []

    for event in events:
        details = _details(event)

        if not _matches_detail_filters(
            details,
            tenant_id=tenant_id,
            actor=actor,
            actor_role=actor_role,
            request_id=request_id,
            correlation_id=correlation_id,
        ):
            continue

        filtered.append(serialize_audit_event(event))

        if len(filtered) >= safe_limit:
            break

    return {
        "status": "success",
        "count": len(filtered),
        "limit": safe_limit,
        "filters": {
            "tenant_id": tenant_id,
            "actor": actor,
            "actor_role": actor_role,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
        },
        "events": filtered,
    }
