from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from sqlalchemy.orm import Session

from app.services.audit_query_service import query_audit_events


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

    return {
        "status": "success",
        "content_type": "text/csv",
        "filename": "lumenai-audit-events-export.csv",
        "count": result["count"],
        "filters": result["filters"],
        "csv": csv_text,
    }
