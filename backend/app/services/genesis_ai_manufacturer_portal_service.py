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

from sqlalchemy.orm import Session

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


def _to_dict(row: ManufacturerKnowledgeUpdate) -> dict:
    return {
        "id": row.id,
        "manufacturer_tenant_id": row.manufacturer_tenant_id,
        "update_type": row.update_type,
        "title": row.title,
        "version": row.version,
        "supersedes_id": row.supersedes_id,
        "body": row.body,
        "instrument_category": row.instrument_category,
        "status": row.status,
        "submitted_by": row.submitted_by,
        "reviewed_by": row.reviewed_by,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "human_review_required": row.human_review_required,
        "created_at": row.created_at.isoformat(),
    }


def _get_or_404(db: Session, update_id: int) -> ManufacturerKnowledgeUpdate:
    row = db.query(ManufacturerKnowledgeUpdate).filter(ManufacturerKnowledgeUpdate.id == update_id).first()
    if row is None:
        raise UnknownManufacturerUpdateError(f"Manufacturer knowledge update {update_id} not found.")
    return row


def submit_update(
    db: Session, manufacturer_tenant_id: str, *, update_type: str, title: str, version: str = "1.0",
    body: str = "", instrument_category: str = "", submitted_by: str, supersedes_id: int | None = None,
) -> dict:
    if update_type not in MANUFACTURER_UPDATE_TYPES:
        raise ValueError(f"update_type must be one of {MANUFACTURER_UPDATE_TYPES}")
    if supersedes_id is not None:
        _get_or_404(db, supersedes_id)
    row = ManufacturerKnowledgeUpdate(
        manufacturer_tenant_id=manufacturer_tenant_id, update_type=update_type, title=title, version=version,
        supersedes_id=supersedes_id, body=body, instrument_category=instrument_category,
        status=MFR_UPDATE_PENDING_REVIEW, submitted_by=submitted_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def review_update(db: Session, update_id: int, *, decision: str, reviewed_by: str) -> dict:
    row = _get_or_404(db, update_id)
    if row.status != MFR_UPDATE_PENDING_REVIEW:
        raise InvalidManufacturerUpdateStateError(f"Update {update_id} is '{row.status}', not pending review.")
    if decision not in ("published", "rejected"):
        raise ValueError("decision must be 'published' or 'rejected'")
    row.status = MFR_UPDATE_PUBLISHED if decision == "published" else MFR_UPDATE_DRAFT
    row.reviewed_by = reviewed_by
    row.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def get_update(db: Session, update_id: int) -> dict:
    return _to_dict(_get_or_404(db, update_id))


def list_updates(
    db: Session, *, manufacturer_tenant_id: str = "", update_type: str = "", status: str = "",
) -> list[dict]:
    query = db.query(ManufacturerKnowledgeUpdate)
    if manufacturer_tenant_id:
        query = query.filter(ManufacturerKnowledgeUpdate.manufacturer_tenant_id == manufacturer_tenant_id)
    if update_type:
        if update_type not in MANUFACTURER_UPDATE_TYPES:
            raise ValueError(f"update_type must be one of {MANUFACTURER_UPDATE_TYPES}")
        query = query.filter(ManufacturerKnowledgeUpdate.update_type == update_type)
    if status:
        if status not in MFR_UPDATE_STATUSES:
            raise ValueError(f"status must be one of {MFR_UPDATE_STATUSES}")
        query = query.filter(ManufacturerKnowledgeUpdate.status == status)
    rows = query.order_by(ManufacturerKnowledgeUpdate.created_at.desc()).all()
    return [_to_dict(r) for r in rows]


def version_chain(db: Session, update_id: int) -> list[dict]:
    """Walks backward through `supersedes_id`, oldest first -- the same
    version-chain-walker pattern used across this codebase."""
    chain: list[ManufacturerKnowledgeUpdate] = []
    current: ManufacturerKnowledgeUpdate | None = _get_or_404(db, update_id)
    seen: set[int] = set()
    while current is not None and current.id not in seen:
        seen.add(current.id)
        chain.append(current)
        current = (
            db.query(ManufacturerKnowledgeUpdate).filter(ManufacturerKnowledgeUpdate.id == current.supersedes_id).first()
            if current.supersedes_id is not None else None
        )
    return [_to_dict(r) for r in reversed(chain)]
