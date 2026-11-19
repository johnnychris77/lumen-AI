"""v5.3 — Project Genesis AI, Section 4: Manufacturer Knowledge Portal.

Beacon's `beacon_manufacturer_portal_service.py` (v3.5) is read-only
analytics *for* a manufacturer to view its own instrument population's
quality trends -- nothing lets a manufacturer *publish* version-
controlled IFU/guidance updates. `ManufacturerKnowledgeUpdate` (this
sprint) is the write side: "All updates are version-controlled and
reviewable" -- `supersedes_id` forms a real version chain (the same
pattern as `QualityPolicy`/`StandardsPublication`), and `status` can
only reach `published` through an explicit `review_update` call.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.services.enterprise_audit_service import record_enterprise_audit_event
from app.models.genesis_ai_intelligence_cloud import (
    MANUFACTURER_UPDATE_TYPES,
    MFR_UPDATE_DRAFT,
    MFR_UPDATE_PENDING_REVIEW,
    MFR_UPDATE_PUBLISHED,
    MFR_UPDATE_STATUSES,
    ManufacturerKnowledgeUpdate,
)


class UnknownManufacturerUpdateError(Exception):
    pass


class InvalidManufacturerUpdateStateError(Exception):
    pass


def _to_dict(row: ManufacturerKnowledgeUpdate, caller_tenant_id: str | None = None) -> dict:
    """Serialize an update for ``caller_tenant_id``.

    P472-03 B6.1 (fail closed, pending GD-6): a caller outside the submitting
    tenant never sees who submitted or reviewed it, nor the submitting tenant's
    id ("hospital identities in cross-hospital intelligence must be anonymized").
    ``caller_tenant_id=None`` is the internal/owner view.
    """
    owner = caller_tenant_id is None or row.manufacturer_tenant_id == caller_tenant_id
    return {
        "id": row.id,
        "manufacturer_tenant_id": row.manufacturer_tenant_id if owner else None,
        "owned_by_caller": owner,
        "update_type": row.update_type,
        "title": row.title,
        "version": row.version,
        "supersedes_id": row.supersedes_id,
        "body": row.body,
        "instrument_category": row.instrument_category,
        "status": row.status,
        "submitted_by": row.submitted_by if owner else None,
        "reviewed_by": row.reviewed_by if owner else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "human_review_required": row.human_review_required,
        "created_at": row.created_at.isoformat(),
    }


def _visible_to(row: ManufacturerKnowledgeUpdate, caller_tenant_id: str) -> bool:
    """Fail closed (P472-03 B6.1, pending GD-6): an update is visible to its
    submitting tenant; to everyone else only once it is published."""
    return row.manufacturer_tenant_id == caller_tenant_id or row.status == MFR_UPDATE_PUBLISHED


def _get_or_404(db: Session, update_id: int) -> ManufacturerKnowledgeUpdate:
    row = db.query(ManufacturerKnowledgeUpdate).filter(ManufacturerKnowledgeUpdate.id == update_id).first()
    if row is None:
        raise UnknownManufacturerUpdateError(f"Manufacturer knowledge update {update_id} not found.")
    return row


def _get_visible_or_404(db: Session, update_id: int, caller_tenant_id: str) -> ManufacturerKnowledgeUpdate:
    row = db.query(ManufacturerKnowledgeUpdate).filter(ManufacturerKnowledgeUpdate.id == update_id).first()
    if row is None or not _visible_to(row, caller_tenant_id):
        # Same answer as a non-existent id: no existence oracle.
        raise UnknownManufacturerUpdateError(f"Manufacturer knowledge update {update_id} not found.")
    return row


def _get_owned_or_404(db: Session, update_id: int, caller_tenant_id: str) -> ManufacturerKnowledgeUpdate:
    row = db.query(ManufacturerKnowledgeUpdate).filter(ManufacturerKnowledgeUpdate.id == update_id).first()
    if row is None or row.manufacturer_tenant_id != caller_tenant_id:
        raise UnknownManufacturerUpdateError(f"Manufacturer knowledge update {update_id} not found.")
    return row


def submit_update(
    db: Session, manufacturer_tenant_id: str, *, update_type: str, title: str, version: str = "1.0",
    body: str = "", instrument_category: str = "", submitted_by: str, supersedes_id: int | None = None,
) -> dict:
    if update_type not in MANUFACTURER_UPDATE_TYPES:
        raise ValueError(f"update_type must be one of {MANUFACTURER_UPDATE_TYPES}")
    if supersedes_id is not None:
        # B6.1: an update may only supersede the submitting tenant's own update.
        _get_owned_or_404(db, supersedes_id, manufacturer_tenant_id)
    row = ManufacturerKnowledgeUpdate(
        manufacturer_tenant_id=manufacturer_tenant_id, update_type=update_type, title=title, version=version,
        supersedes_id=supersedes_id, body=body, instrument_category=instrument_category,
        status=MFR_UPDATE_PENDING_REVIEW, submitted_by=submitted_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def review_update(
    db: Session, update_id: int, *, decision: str, reviewed_by: str, caller_tenant_id: str,
) -> dict:
    """Publish or reject an update of the CALLER'S OWN tenant.

    P472-03 B6.1 (fail closed, pending GD-6): reviewing another tenant's update
    is refused (404, indistinguishable from a missing id). Cross-tenant
    moderation needs a separately authorized curator role that GD-6 has not
    defined — no such role is designated here. Every decision is audited.
    """
    row = _get_owned_or_404(db, update_id, caller_tenant_id)
    if row.status != MFR_UPDATE_PENDING_REVIEW:
        raise InvalidManufacturerUpdateStateError(f"Update {update_id} is '{row.status}', not pending review.")
    if decision not in ("published", "rejected"):
        raise ValueError("decision must be 'published' or 'rejected'")
    previous = row.status
    row.status = MFR_UPDATE_PUBLISHED if decision == "published" else MFR_UPDATE_DRAFT
    row.reviewed_by = reviewed_by
    row.reviewed_at = datetime.now(timezone.utc)
    record_enterprise_audit_event(
        db, action_type=f"genesis.manufacturer_update.{decision}", resource_type="genesis_manufacturer_update",
        resource_id=str(row.id), actor=reviewed_by, actor_email=reviewed_by, tenant_id=caller_tenant_id,
        details={"decision": decision, "status_before": previous, "status_after": row.status}, commit=False,
    )
    db.commit()
    db.refresh(row)
    return _to_dict(row, caller_tenant_id)


def get_update(db: Session, update_id: int, caller_tenant_id: str) -> dict:
    return _to_dict(_get_visible_or_404(db, update_id, caller_tenant_id), caller_tenant_id)


def list_updates(
    db: Session, *, caller_tenant_id: str, own_only: bool = False, update_type: str = "", status: str = "",
) -> list[dict]:
    """Updates visible to the caller: its own (any status) and published ones.
    ``own_only`` restricts to the caller's own updates (the former publisher
    filter, which may now only name the caller's own tenant)."""
    query = db.query(ManufacturerKnowledgeUpdate)
    if own_only:
        query = query.filter(ManufacturerKnowledgeUpdate.manufacturer_tenant_id == caller_tenant_id)
    else:
        query = query.filter(or_(ManufacturerKnowledgeUpdate.manufacturer_tenant_id == caller_tenant_id,
                                 ManufacturerKnowledgeUpdate.status == MFR_UPDATE_PUBLISHED))
    if update_type:
        if update_type not in MANUFACTURER_UPDATE_TYPES:
            raise ValueError(f"update_type must be one of {MANUFACTURER_UPDATE_TYPES}")
        query = query.filter(ManufacturerKnowledgeUpdate.update_type == update_type)
    if status:
        if status not in MFR_UPDATE_STATUSES:
            raise ValueError(f"status must be one of {MFR_UPDATE_STATUSES}")
        query = query.filter(ManufacturerKnowledgeUpdate.status == status)
    rows = query.order_by(ManufacturerKnowledgeUpdate.created_at.desc()).all()
    return [_to_dict(r, caller_tenant_id) for r in rows]


def version_chain(db: Session, update_id: int, caller_tenant_id: str) -> list[dict]:
    """Walks backward through `supersedes_id`, oldest first. Only versions the
    caller may see are returned (B6.1); the starting version must be visible."""
    chain: list[ManufacturerKnowledgeUpdate] = []
    current: ManufacturerKnowledgeUpdate | None = _get_visible_or_404(db, update_id, caller_tenant_id)
    seen: set[int] = set()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        if _visible_to(current, caller_tenant_id):
            chain.append(current)
        current = (
            db.query(ManufacturerKnowledgeUpdate).filter(ManufacturerKnowledgeUpdate.id == current.supersedes_id).first()
            if current.supersedes_id is not None else None
        )
    return [_to_dict(r, caller_tenant_id) for r in reversed(chain)]
