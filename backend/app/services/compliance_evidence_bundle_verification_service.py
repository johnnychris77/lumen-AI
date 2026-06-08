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


def verify_compliance_evidence_bundle_hash(
    db: Session,
    *,
    bundle_hash: str,
) -> dict[str, Any]:
    normalized_hash = (bundle_hash or "").strip()

    if not normalized_hash:
        return {
            "status": "success",
            "verified": False,
            "bundle_hash": normalized_hash,
            "bundle_hash_algorithm": "SHA-256",
            "event_id": None,
            "message": "No compliance evidence bundle hash provided.",
        }

    event = (
        db.query(AuditLog)
        .filter(
            AuditLog.action_type == "compliance_evidence_bundle_generated",
            AuditLog.resource_type == "compliance_evidence_bundle",
            AuditLog.resource_id == normalized_hash,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )

    if not event:
        return {
            "status": "success",
            "verified": False,
            "bundle_hash": normalized_hash,
            "bundle_hash_algorithm": "SHA-256",
            "event_id": None,
            "message": "No matching compliance evidence bundle event found.",
        }

    details = _details(event)

    stored_bundle_hash = details.get("bundle_hash") or event.resource_id
    verified = stored_bundle_hash == normalized_hash

    return {
        "status": "success",
        "verified": verified,
        "bundle_hash": normalized_hash,
        "bundle_hash_algorithm": details.get("bundle_hash_algorithm", "SHA-256"),
        "event_id": event.id,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "action_type": event.action_type,
        "audit_export_hash": details.get("audit_export_hash", ""),
        "audit_export_hash_algorithm": details.get("audit_export_hash_algorithm", "SHA-256"),
        "manifest_hash": details.get("manifest_hash", ""),
        "manifest_hash_algorithm": details.get("manifest_hash_algorithm", "SHA-256"),
        "audit_export_event_id": details.get("audit_export_event_id"),
        "generated_at": details.get("generated_at", ""),
        "generated_by": details.get("generated_by", ""),
        "generated_role": details.get("generated_role", ""),
        "export_count": details.get("export_count"),
        "filters": details.get("filters", {}),
        "tamper_evident": bool(details.get("tamper_evident", False)),
        "bundle": details.get("bundle", {}),
        "message": "Compliance evidence bundle hash verified." if verified else "Compliance evidence bundle hash mismatch.",
    }
