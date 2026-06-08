from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from io import StringIO
from typing import Any

from sqlalchemy.orm import Session

from app.services.audit_query_service import query_audit_events
from app.services.enterprise_audit_service import record_enterprise_audit_event


AUDIT_CSV_FIELDS = [
    "id",
    "created_at",
    "action_type",
    "resource_type",
    "resource_id",
    "actor",
    "actor_role",
    "tenant_id",
    "tenant_name",
    "request_id",
    "correlation_id",
    "auth_provider",
    "issuer",
    "event_hash",
    "previous_event_hash",
]


def export_audit_events_csv(
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
    limit: int = 200,
) -> dict[str, Any]:
    result = query_audit_events(
        db,
        tenant_id=tenant_id,
        actor=actor,
        actor_role=actor_role,
        request_id=request_id,
        correlation_id=correlation_id,
        action_type=action_type,
        resource_type=resource_type,
        resource_id=resource_id,
        limit=limit,
    )

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=AUDIT_CSV_FIELDS)
    writer.writeheader()

    for event in result["events"]:
        writer.writerow({field: event.get(field, "") for field in AUDIT_CSV_FIELDS})

    csv_text = output.getvalue()
    export_hash = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()
    exported_at = datetime.now(UTC).isoformat()

    manifest = {
        "manifest_type": "lumenai_audit_export_manifest",
        "filename": "lumenai-audit-events-export.csv",
        "content_type": "text/csv",
        "exported_at": exported_at,
        "export_count": result["count"],
        "filters": result["filters"],
        "csv_hash": export_hash,
        "csv_hash_algorithm": "SHA-256",
        "verification_url": f"/api/enterprise/audit/events/export/verify?audit_export_hash={export_hash}",
        "tamper_evident": True,
    }

    manifest_json = json.dumps(manifest, sort_keys=True, separators=(",", ":"), default=str)
    manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()

    return {
        "status": "success",
        "content_type": "text/csv",
        "filename": "lumenai-audit-events-export.csv",
        "count": result["count"],
        "filters": result["filters"],
        "csv": csv_text,
        "audit_export_hash": export_hash,
        "audit_export_hash_algorithm": "SHA-256",
        "exported_at": exported_at,
        "manifest": manifest,
        "manifest_json": manifest_json,
        "manifest_hash": manifest_hash,
        "manifest_hash_algorithm": "SHA-256",
    }


def record_audit_export_event(
    db: Session,
    *,
    actor: str,
    actor_role: str,
    export_result: dict[str, Any],
) -> object:
    return record_enterprise_audit_event(
        db,
        action_type="audit_events_csv_exported",
        resource_type="enterprise_audit_export",
        resource_id=export_result["audit_export_hash"],
        actor=actor,
        actor_role=actor_role,
        packet_hash=export_result["audit_export_hash"],
        packet_hash_algorithm=export_result["audit_export_hash_algorithm"],
        details={
            "filename": export_result["filename"],
            "content_type": export_result["content_type"],
            "export_count": export_result["count"],
            "exported_at": export_result["exported_at"],
            "audit_export_hash": export_result["audit_export_hash"],
            "audit_export_hash_algorithm": export_result["audit_export_hash_algorithm"],
            "manifest_hash": export_result.get("manifest_hash"),
            "manifest_hash_algorithm": export_result.get("manifest_hash_algorithm"),
            "manifest": export_result.get("manifest"),
            "filters": export_result["filters"],
            "tamper_evident": True,
        },
    )
