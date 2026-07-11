from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from fastapi import Request
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.auth.audit_context import merge_auth_context_into_details
from app.auth.context import AuthContext


def _safe_details(details: dict[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}

    return {
        str(key): value
        for key, value in details.items()
        if value is not None
    }




def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _deserialize_details(raw_details: Any) -> dict[str, Any]:
    if not raw_details:
        return {}

    if isinstance(raw_details, dict):
        return raw_details

    if isinstance(raw_details, str):
        try:
            return json.loads(raw_details)
        except json.JSONDecodeError:
            return {"raw_details": raw_details}

    return {"raw_details": str(raw_details)}


def _latest_event_hash_for_resource(
    db: Session,
    *,
    resource_type: str,
    resource_id: str,
) -> str:
    if "resource_type" not in _auditlog_columns() or "resource_id" not in _auditlog_columns():
        return ""

    latest_event = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )

    if not latest_event:
        return ""

    details = _deserialize_details(getattr(latest_event, "details", None))
    return str(details.get("event_hash") or "")


def _build_event_hash_payload(
    *,
    action_type: str,
    resource_type: str,
    resource_id: str,
    actor: str,
    actor_role: str,
    details: dict[str, Any],
    previous_event_hash: str,
) -> dict[str, Any]:
    payload_details = dict(details)
    payload_details.pop("event_hash", None)
    payload_details.pop("previous_event_hash", None)

    return {
        "action_type": action_type,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "actor": actor,
        "actor_role": actor_role,
        "details": payload_details,
        "previous_event_hash": previous_event_hash,
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
    actor_email: str | None = None,
    actor_role: str = "system",
    tenant_id: str | None = None,
    tenant_name: str | None = None,
    status: str = "success",
    compliance_flag: bool = False,
    finding_id: int | None = None,
    baseline_id: int | None = None,
    packet_hash: str | None = None,
    packet_hash_algorithm: str | None = None,
    details: dict[str, Any] | None = None,
    auth_context: AuthContext | None = None,
    request: Request | None = None,
    commit: bool = True,
) -> AuditLog:
    """
    Centralized enterprise audit writer.

    This service is intentionally append-only and hash-chains every event
    per (resource_type, resource_id) -- see verify_audit_chain() in
    audit_chain_verification_service.py. It also adapts to the current
    AuditLog schema by placing fields into direct columns when available and
    into details when the column does not exist yet.

    This is the single writer for LumenAI audit events. app.audit.log_audit_event
    is a deprecated compatibility shim that delegates here.
    """

    columns = _auditlog_columns()

    details = merge_auth_context_into_details(details, auth_context, request=request)
    safe_details = _safe_details(details)

    resolved_actor = actor or "system"
    resolved_actor_role = actor_role or "system"
    resolved_actor_email = actor_email if actor_email is not None else resolved_actor
    resolved_tenant_name = tenant_name if tenant_name is not None else (tenant_id or "")

    # NOTE: this normalized/safe_details step (and therefore the event hash
    # payload built from safe_details below) is intentionally unchanged from
    # before actor_email/tenant_name/status/compliance_flag were added as
    # real columns -- those new fields are written directly to columns
    # further down and never enter `details`, so they don't affect hash
    # computation for any existing caller. Callers that need tenant_id/
    # actor_role to also be queryable via audit_query_service.py (which
    # reads `details`, not columns) should include them in `details=`
    # explicitly, the same way auth_context=... already does via
    # to_audit_details().
    normalized = {
        "actor": resolved_actor,
        "actor_role": resolved_actor_role,
        "tenant_id": tenant_id,
        "finding_id": finding_id,
        "baseline_id": baseline_id,
        "packet_hash": packet_hash,
        "packet_hash_algorithm": packet_hash_algorithm,
    }

    for key, value in normalized.items():
        if value is not None and key not in columns:
            safe_details.setdefault(key, value)

    normalized_resource_id = str(resource_id) if resource_id is not None else ""
    previous_event_hash = _latest_event_hash_for_resource(
        db,
        resource_type=resource_type,
        resource_id=normalized_resource_id,
    )

    event_hash_payload = _build_event_hash_payload(
        action_type=action_type,
        resource_type=resource_type,
        resource_id=normalized_resource_id,
        actor=resolved_actor,
        actor_role=resolved_actor_role,
        details=safe_details,
        previous_event_hash=previous_event_hash,
    )

    safe_details.setdefault("previous_event_hash", previous_event_hash)
    safe_details.setdefault("event_hash", _sha256(event_hash_payload))
    safe_details.setdefault("event_hash_algorithm", "SHA-256")

    kwargs: dict[str, Any] = {}

    candidate_values = {
        "action_type": action_type,
        "resource_type": resource_type,
        "resource_id": normalized_resource_id,
        "actor": resolved_actor,
        "actor_email": resolved_actor_email,
        "actor_role": resolved_actor_role,
        "tenant_id": tenant_id,
        "tenant_name": resolved_tenant_name or None,
        "status": status,
        "compliance_flag": compliance_flag,
        "request_method": request.method if request else None,
        "request_path": str(request.url.path) if request else None,
        "client_ip": (request.client.host if request and request.client else None),
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
