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


def verify_audit_export_hash(
    db: Session,
    *,
    audit_export_hash: str,
) -> dict[str, Any]:
    normalized_hash = (audit_export_hash or "").strip()

    if not normalized_hash:
        return {
            "status": "success",
            "verified": False,
            "audit_export_hash": normalized_hash,
            "audit_export_hash_algorithm": "SHA-256",
            "event_id": None,
            "message": "No audit export hash provided.",
        }

    event = (
        db.query(AuditLog)
        .filter(
            AuditLog.action_type == "audit_events_csv_exported",
            AuditLog.resource_type == "enterprise_audit_export",
            AuditLog.resource_id == normalized_hash,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )

    if not event:
        return {
            "status": "success",
            "verified": False,
            "audit_export_hash": normalized_hash,
            "audit_export_hash_algorithm": "SHA-256",
            "event_id": None,
            "message": "No matching audit export event found.",
        }

    details = _details(event)
    stored_hash = details.get("audit_export_hash") or event.resource_id

    verified = stored_hash == normalized_hash

    return {
        "status": "success",
        "verified": verified,
        "audit_export_hash": normalized_hash,
        "audit_export_hash_algorithm": details.get("audit_export_hash_algorithm", "SHA-256"),
        "event_id": event.id,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "action_type": event.action_type,
        "filename": details.get("filename", ""),
        "content_type": details.get("content_type", ""),
        "export_count": details.get("export_count"),
        "exported_at": details.get("exported_at", ""),
        "tamper_evident": bool(details.get("tamper_evident", False)),
        "filters": details.get("filters", {}),
        "message": "Audit export hash verified." if verified else "Audit export hash mismatch.",
    }
