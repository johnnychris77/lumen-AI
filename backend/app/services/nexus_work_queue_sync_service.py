"""v3.2 — Project Nexus, Section 4: Work Queue Synchronization.

Links internal work-queue items (inspections, repairs, vendor trays,
loaner instruments, pending cases) to their external-system counterparts.
Every internal_ref_id is validated against the real internal table before
a link is created — a queue item that doesn't exist is never linked, let
alone fabricated. Per the sprint's explicit instruction ("Do not overwrite
external systems without explicit configuration"), `sync_direction`
defaults to `import_only`; only a caller that explicitly passes
`sync_direction="export_enabled"` may have this link used to push data
back out (the actual outbound call is a connector-adapter concern, not
this service's).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.nexus_integration import (
    NEXUS_QUEUE_TYPES,
    NEXUS_SYNC_DIRECTIONS,
    QUEUE_INSPECTION,
    QUEUE_LOANER,
    QUEUE_PENDING_CASE,
    QUEUE_REPAIR,
    QUEUE_VENDOR_TRAY,
    SYNC_DIRECTION_IMPORT_ONLY,
    NexusWorkQueueLink,
)
from app.models.or_connect import RepairRequest, SurgicalCase, VendorTray


class UnknownInternalReferenceError(Exception):
    pass


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _validate_internal_ref(db: Session, tenant_id: str, queue_type: str, internal_ref_id: str) -> None:
    try:
        ref_id = int(internal_ref_id)
    except (TypeError, ValueError):
        raise UnknownInternalReferenceError(f"internal_ref_id '{internal_ref_id}' is not a valid id.") from None

    if queue_type in (QUEUE_INSPECTION, QUEUE_LOANER):
        exists = db.query(models.Inspection.id).filter(models.Inspection.id == ref_id, models.Inspection.tenant_id == tenant_id).first()
    elif queue_type == QUEUE_REPAIR:
        exists = db.query(RepairRequest.id).filter(RepairRequest.id == ref_id, RepairRequest.tenant_id == tenant_id).first()
    elif queue_type == QUEUE_VENDOR_TRAY:
        exists = db.query(VendorTray.id).filter(VendorTray.id == ref_id, VendorTray.tenant_id == tenant_id).first()
    elif queue_type == QUEUE_PENDING_CASE:
        exists = db.query(SurgicalCase.id).filter(SurgicalCase.id == ref_id, SurgicalCase.tenant_id == tenant_id).first()
    else:
        raise ValueError(f"queue_type must be one of {NEXUS_QUEUE_TYPES}")

    if exists is None:
        raise UnknownInternalReferenceError(f"No {queue_type} record with id {internal_ref_id} exists for this tenant.")


def sync_work_queue_link(
    db: Session, tenant_id: str, connector_id: int, *, queue_type: str, internal_ref_id: str,
    external_ref_id: str = "", sync_direction: str = SYNC_DIRECTION_IMPORT_ONLY,
) -> dict:
    if queue_type not in NEXUS_QUEUE_TYPES:
        raise ValueError(f"queue_type must be one of {NEXUS_QUEUE_TYPES}")
    if sync_direction not in NEXUS_SYNC_DIRECTIONS:
        raise ValueError(f"sync_direction must be one of {NEXUS_SYNC_DIRECTIONS}")

    _validate_internal_ref(db, tenant_id, queue_type, internal_ref_id)

    existing = (
        db.query(NexusWorkQueueLink)
        .filter(
            NexusWorkQueueLink.tenant_id == tenant_id, NexusWorkQueueLink.connector_id == connector_id,
            NexusWorkQueueLink.queue_type == queue_type, NexusWorkQueueLink.internal_ref_id == internal_ref_id,
        )
        .first()
    )
    if existing is not None:
        existing.external_ref_id = external_ref_id or existing.external_ref_id
        existing.sync_direction = sync_direction
        existing.last_synced_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return _row_to_dict(existing)

    row = NexusWorkQueueLink(
        connector_id=connector_id, tenant_id=tenant_id, queue_type=queue_type, internal_ref_id=internal_ref_id,
        external_ref_id=external_ref_id, sync_direction=sync_direction,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def list_work_queue_links(db: Session, tenant_id: str, connector_id: int, *, queue_type: str = "") -> list[dict]:
    q = db.query(NexusWorkQueueLink).filter(NexusWorkQueueLink.tenant_id == tenant_id, NexusWorkQueueLink.connector_id == connector_id)
    if queue_type:
        q = q.filter(NexusWorkQueueLink.queue_type == queue_type)
    return [_row_to_dict(r) for r in q.order_by(NexusWorkQueueLink.id.desc()).all()]
