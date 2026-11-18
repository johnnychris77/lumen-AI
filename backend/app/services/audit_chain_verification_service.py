from __future__ import annotations

import hashlib
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
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw_details": raw}

    return {"raw_details": str(raw)}


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _event_hash_payload(event: AuditLog, details: dict[str, Any], previous_event_hash: str) -> dict[str, Any]:
    clean_details = dict(details)
    clean_details.pop("event_hash", None)
    clean_details.pop("previous_event_hash", None)
    clean_details.pop("event_hash_algorithm", None)

    return {
        "action_type": getattr(event, "action_type", ""),
        "resource_type": getattr(event, "resource_type", ""),
        "resource_id": getattr(event, "resource_id", ""),
        "actor": clean_details.get("actor") or getattr(event, "actor", "system"),
        "actor_role": clean_details.get("actor_role") or getattr(event, "actor_role", "system"),
        "details": clean_details,
        "previous_event_hash": previous_event_hash,
    }


class AuditChainScopeError(Exception):
    """The chain contains events outside the caller's tenant and may not be
    verified for that caller (governance decision GD-2)."""


def verify_audit_chain(
    db: Session,
    *,
    resource_type: str,
    resource_id: str,
    owner_tenant_id: str | None = None,
) -> dict[str, Any]:
    """Verify the hash chain of one resource.

    ``owner_tenant_id`` is the caller's verified tenant (governance decision
    GD-2). A chain is verified in full or not at all, so it is never filtered:

    * no event of the chain belongs to the caller's tenant -> the caller is told
      exactly what they are told for a resource with no events;
    * every event belongs to the caller's tenant -> normal verification;
    * the chain mixes the caller's events with events of another tenant, or of
      none -> ``AuditChainScopeError``. Verifying it is a cross-tenant operation.

    With no ``owner_tenant_id`` the chain is verified regardless of tenant. The
    enterprise quality routes always pass it. The GuardianX replay service does
    not yet (it also loads its subject by id with no tenant check; recorded as an
    open finding, AW-08).
    """
    events = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == str(resource_id),
        )
        .order_by(AuditLog.id.asc())
        .all()
    )

    if owner_tenant_id is not None and events:
        tenants = {(event.tenant_id or "") for event in events}
        if owner_tenant_id not in tenants:
            events = []
        elif tenants != {owner_tenant_id}:
            raise AuditChainScopeError(
                "This audit chain contains records outside your tenant. "
                "Verifying it requires an authorized platform-security review."
            )

    if not events:
        return {
            "verified": True,
            "resource_type": resource_type,
            "resource_id": str(resource_id),
            "event_count": 0,
            "broken_event_id": None,
            "message": "No audit events found for this resource.",
        }

    expected_previous_hash = ""

    for event in events:
        details = _details(event)

        stored_previous_hash = str(details.get("previous_event_hash") or "")
        stored_event_hash = str(details.get("event_hash") or "")

        if not stored_event_hash:
            return {
                "verified": False,
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "event_count": len(events),
                "broken_event_id": event.id,
                "message": "Audit event is missing event_hash.",
            }

        if stored_previous_hash != expected_previous_hash:
            return {
                "verified": False,
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "event_count": len(events),
                "broken_event_id": event.id,
                "message": "Audit event previous hash does not match expected chain value.",
            }

        recalculated_hash = _sha256(
            _event_hash_payload(
                event,
                details,
                stored_previous_hash,
            )
        )

        if recalculated_hash != stored_event_hash:
            return {
                "verified": False,
                "resource_type": resource_type,
                "resource_id": str(resource_id),
                "event_count": len(events),
                "broken_event_id": event.id,
                "message": "Audit event hash does not match recalculated event payload.",
            }

        expected_previous_hash = stored_event_hash

    return {
        "verified": True,
        "resource_type": resource_type,
        "resource_id": str(resource_id),
        "event_count": len(events),
        "broken_event_id": None,
        "message": "Audit chain verified successfully.",
    }
