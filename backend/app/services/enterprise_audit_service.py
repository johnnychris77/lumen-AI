from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def _safe_details(details: dict[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}

    return {
        str(key): value
        for key, value in details.items()
        if value is not None
    }



def _serialize_details_for_auditlog(details: dict[str, Any]) -> Any:
    details_column = AuditLog.__table__.columns.get("details")

    if details_column is None:
        return details

    column_type = details_column.type.__class__.__name__.lower()

    if "json" in column_type:
        return details

    return json.dumps(details, sort_keys=True, default=str)

def _auditlog_columns() -> set[str]:
    return {column.name for column in AuditLog.__table__.columns}


def record_enterprise_audit_event(
    db: Session,
    *,
    action_type: str,
    resource_type: str,
    resource_id: str | int | None = None,
    actor: str = "system",
    actor_role: str = "system",
    tenant_id: str | None = None,
    finding_id: int | None = None,
    baseline_id: int | None = None,
    packet_hash: str | None = None,
    packet_hash_algorithm: str | None = None,
    details: dict[str, Any] | None = None,
    commit: bool = True,
) -> AuditLog:
    """
    Centralized enterprise audit writer.

    This service is intentionally append-only. It also adapts to the current
    AuditLog schema by placing fields into direct columns when available and
    into details when the column does not exist yet.
    """

    columns = _auditlog_columns()

    safe_details = _safe_details(details)

    normalized = {
        "actor": actor or "system",
        "actor_role": actor_role or "system",
        "tenant_id": tenant_id,
        "finding_id": finding_id,
        "baseline_id": baseline_id,
        "packet_hash": packet_hash,
        "packet_hash_algorithm": packet_hash_algorithm,
    }

    for key, value in normalized.items():
        if value is not None and key not in columns:
            safe_details.setdefault(key, value)

    kwargs: dict[str, Any] = {}

    candidate_values = {
        "action_type": action_type,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id is not None else "",
        "actor": actor or "system",
        "actor_role": actor_role or "system",
        "tenant_id": tenant_id,
        "finding_id": finding_id,
        "baseline_id": baseline_id,
        "packet_hash": packet_hash,
        "packet_hash_algorithm": packet_hash_algorithm,
        "details": _serialize_details_for_auditlog(safe_details),
        "created_at": datetime.now(UTC),
    }

    for key, value in candidate_values.items():
        if key in columns and value is not None:
            kwargs[key] = value

    event = AuditLog(**kwargs)

    db.add(event)

    if commit:
        db.commit()
        db.refresh(event)

    return event


def record_system_audit_event(
    db: Session,
    *,
    action_type: str,
    resource_type: str,
    resource_id: str | int | None = None,
    details: dict[str, Any] | None = None,
    commit: bool = True,
) -> AuditLog:
    return record_enterprise_audit_event(
        db,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        actor="system",
        actor_role="system",
        details=details,
        commit=commit,
    )
