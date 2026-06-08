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


def verify_audit_chain(
    db: Session,
    *,
    resource_type: str,
    resource_id: str,
) -> dict[str, Any]:
    events = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == str(resource_id),
        )
        .order_by(AuditLog.id.asc())
        .all()
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
