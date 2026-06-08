from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.services.audit_export_service import export_audit_events_csv, record_audit_export_event


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def build_compliance_evidence_bundle(
    db: Session,
    *,
    actor: str,
    actor_role: str,
    tenant_id: str | None = None,
    actor_filter: str | None = None,
    actor_role_filter: str | None = None,
    request_id: str | None = None,
    correlation_id: str | None = None,
    action_type: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    export = export_audit_events_csv(
        db,
        tenant_id=tenant_id,
        actor=actor_filter,
        actor_role=actor_role_filter,
        request_id=request_id,
        correlation_id=correlation_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )

    export_event = record_audit_export_event(
        db,
        actor=actor,
        actor_role=actor_role,
        export_result=export,
    )

    bundle = {
        "bundle_type": "lumenai_compliance_evidence_bundle",
        "bundle_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "generated_by": actor,
        "generated_role": actor_role,
        "tamper_evident": True,
        "audit_export": {
            "filename": export["filename"],
            "content_type": export["content_type"],
            "count": export["count"],
            "filters": export["filters"],
            "exported_at": export["exported_at"],
            "audit_export_hash": export["audit_export_hash"],
            "audit_export_hash_algorithm": export["audit_export_hash_algorithm"],
            "audit_export_verification_url": (
                "/api/enterprise/audit/events/export/verify"
                f"?audit_export_hash={export['audit_export_hash']}"
            ),
        },
        "manifest": {
            "manifest": export["manifest"],
            "manifest_hash": export["manifest_hash"],
            "manifest_hash_algorithm": export["manifest_hash_algorithm"],
            "manifest_verification_url": (
                "/api/enterprise/audit/events/export/manifest/verify"
                f"?manifest_hash={export['manifest_hash']}"
            ),
        },
        "audit_event": {
            "event_id": export_event.id,
            "action_type": export_event.action_type,
            "resource_type": export_event.resource_type,
            "resource_id": export_event.resource_id,
        },
        "compliance_controls": [
            "centralized_audit_logging",
            "audit_event_integrity_hash",
            "audit_chain_verification",
            "request_correlation_id",
            "filtered_audit_export",
            "audit_export_hash",
            "audit_export_manifest",
            "manifest_verification",
        ],
    }

    bundle_json = _canonical_json(bundle)
    bundle_hash = hashlib.sha256(bundle_json.encode("utf-8")).hexdigest()

    bundle["bundle_hash"] = bundle_hash
    bundle["bundle_hash_algorithm"] = "SHA-256"
    bundle["bundle_verification_note"] = (
        "Recompute SHA-256 over canonical bundle JSON excluding bundle_hash "
        "and bundle_hash_algorithm."
    )

    return {
        "status": "success",
        "bundle": bundle,
        "bundle_json": _canonical_json(bundle),
        "bundle_hash": bundle_hash,
        "bundle_hash_algorithm": "SHA-256",
    }
