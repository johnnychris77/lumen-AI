"""Project Veritas, Section 7: Evidence Provenance Ledger.

Records provenance for an evidence object by reference (never duplicating
the underlying bytes/table) -- the same reuse pattern Sage's
`SageEducationImageEntry` established for `RetainedImage`.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.veritas_evidence import EVIDENCE_TYPES, VeritasEvidenceProvenanceRecord


def record_provenance(
    db: Session, tenant_id: str, *, evidence_type: str, source: str = "", organization: str = "",
    facility: str = "", creator: str = "", instrument_id: str = "", inspection_id: int | None = None,
    anatomy_zone: str = "", baseline_id: int | None = None, file_hash: str = "", storage_location: str = "",
    approval_status: str = "", reviewer: str = "", version: str = "1.0.0", usage_scope: str = "internal",
) -> VeritasEvidenceProvenanceRecord:
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"Unknown evidence_type '{evidence_type}'")
    row = VeritasEvidenceProvenanceRecord(
        tenant_id=tenant_id, evidence_type=evidence_type, source=source, organization=organization,
        facility=facility, creator=creator, instrument_id=instrument_id, inspection_id=inspection_id,
        anatomy_zone=anatomy_zone, baseline_id=baseline_id, file_hash=file_hash, storage_location=storage_location,
        approval_status=approval_status, reviewer=reviewer, version=version, usage_scope=usage_scope,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def append_modification(db: Session, tenant_id: str, record_id: int, *, actor: str, change: str) -> VeritasEvidenceProvenanceRecord | None:
    row = (
        db.query(VeritasEvidenceProvenanceRecord)
        .filter(VeritasEvidenceProvenanceRecord.id == record_id, VeritasEvidenceProvenanceRecord.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        return None
    history = json.loads(row.modification_history_json or "[]")
    from datetime import datetime, timezone
    history.append({"actor": actor, "change": change, "at": datetime.now(timezone.utc).isoformat()})
    row.modification_history_json = json.dumps(history)
    db.commit()
    db.refresh(row)
    return row


def to_dict(row: VeritasEvidenceProvenanceRecord) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "evidence_type": row.evidence_type,
        "source": row.source,
        "organization": row.organization,
        "facility": row.facility,
        "creator": row.creator,
        "instrument_id": row.instrument_id,
        "inspection_id": row.inspection_id,
        "anatomy_zone": row.anatomy_zone,
        "baseline_id": row.baseline_id,
        "file_hash": row.file_hash,
        "storage_location": row.storage_location,
        "approval_status": row.approval_status,
        "reviewer": row.reviewer,
        "version": row.version,
        "modification_history": json.loads(row.modification_history_json or "[]"),
        "usage_scope": row.usage_scope,
    }


def list_provenance(db: Session, tenant_id: str, *, inspection_id: int | None = None, evidence_type: str = "") -> list[dict]:
    q = db.query(VeritasEvidenceProvenanceRecord).filter(VeritasEvidenceProvenanceRecord.tenant_id == tenant_id)
    if inspection_id is not None:
        q = q.filter(VeritasEvidenceProvenanceRecord.inspection_id == inspection_id)
    if evidence_type:
        q = q.filter(VeritasEvidenceProvenanceRecord.evidence_type == evidence_type)
    return [to_dict(r) for r in q.order_by(VeritasEvidenceProvenanceRecord.created_at.desc()).all()]
