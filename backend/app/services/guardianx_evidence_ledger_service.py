"""v5.2 — Project GuardianX, Section 8: Evidence Ledger.

Append-only: no function in this module updates or deletes an
`EvidenceLedgerEntry` row. Every entry is paired with a real call to
`enterprise_audit_service.record_enterprise_audit_event` -- the same
hash-chained, tamper-evident writer used platform-wide -- and the
entry's `digital_signature` stores that event's real SHA-256
`event_hash`, never a fabricated signature. `verify_entry` re-runs
`audit_chain_verification_service.verify_audit_chain` to prove the
signature hasn't been tampered with.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.guardianx_assurance import EvidenceLedgerEntry
from app.services.audit_chain_verification_service import verify_audit_chain
from app.services.enterprise_audit_service import record_enterprise_audit_event

_RESOURCE_TYPE = "guardianx_evidence_ledger_entry"


class UnknownEvidenceLedgerEntryError(Exception):
    pass


def _event_hash(audit_row) -> str:
    details = audit_row.details
    if isinstance(details, str):
        details = json.loads(details or "{}")
    return str((details or {}).get("event_hash", ""))


def _to_dict(entry: EvidenceLedgerEntry) -> dict:
    return {
        "id": entry.id,
        "source_type": entry.source_type,
        "source_id": entry.source_id,
        "evidence": json.loads(entry.evidence_json or "[]"),
        "knowledge_version": entry.knowledge_version,
        "model_version": entry.model_version,
        "workflow_version": entry.workflow_version,
        "reviewer": entry.reviewer,
        "digital_signature": entry.digital_signature,
        "human_review_required": entry.human_review_required,
        "disclaimer": entry.disclaimer,
        "recorded_at": entry.recorded_at.isoformat(),
    }


def record_evidence(
    db: Session, *, source_type: str, source_id: str, evidence: list[str], knowledge_version: str = "",
    model_version: str = "", workflow_version: str = "", reviewer: str,
) -> dict:
    row = EvidenceLedgerEntry(
        source_type=source_type, source_id=source_id, evidence_json=json.dumps(evidence),
        knowledge_version=knowledge_version, model_version=model_version, workflow_version=workflow_version,
        reviewer=reviewer,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    audit_row = record_enterprise_audit_event(
        db, action_type="guardianx.evidence_recorded", resource_type=_RESOURCE_TYPE,
        resource_id=str(row.id), actor=reviewer, actor_email=reviewer,
        details={
            "source_type": source_type, "source_id": source_id, "knowledge_version": knowledge_version,
            "model_version": model_version, "workflow_version": workflow_version,
        },
    )
    row.digital_signature = _event_hash(audit_row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get_or_404(db: Session, entry_id: int) -> EvidenceLedgerEntry:
    row = db.query(EvidenceLedgerEntry).filter(EvidenceLedgerEntry.id == entry_id).first()
    if row is None:
        raise UnknownEvidenceLedgerEntryError(f"Evidence ledger entry {entry_id} not found.")
    return row


def get_entry(db: Session, entry_id: int) -> dict:
    return _to_dict(_get_or_404(db, entry_id))


def list_entries_for_source(db: Session, source_type: str, source_id: str) -> list[dict]:
    rows = (
        db.query(EvidenceLedgerEntry)
        .filter(EvidenceLedgerEntry.source_type == source_type, EvidenceLedgerEntry.source_id == source_id)
        .order_by(EvidenceLedgerEntry.recorded_at.asc())
        .all()
    )
    return [_to_dict(r) for r in rows]


def verify_entry(db: Session, entry_id: int) -> dict:
    """Confirms the entry's `digital_signature` is still part of an
    unbroken hash chain -- proof the ledger hasn't been tampered with."""
    entry = _get_or_404(db, entry_id)
    return verify_audit_chain(db, resource_type=_RESOURCE_TYPE, resource_id=str(entry.id))
