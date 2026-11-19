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

import hashlib
import json

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
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


EVIDENCE_DIGEST_KEY = "evidence_sha256"


def evidence_digest(entry: EvidenceLedgerEntry) -> str:
    """SHA-256 over the canonical content of a ledger row (everything but the
    signature and the server timestamps)."""
    payload = {
        "source_type": entry.source_type, "source_id": entry.source_id,
        "evidence": json.loads(entry.evidence_json or "[]"),
        "knowledge_version": entry.knowledge_version, "model_version": entry.model_version,
        "workflow_version": entry.workflow_version, "reviewer": entry.reviewer,
        "human_review_required": bool(entry.human_review_required),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


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
    model_version: str = "", workflow_version: str = "", reviewer: str, tenant_id: str | None = None,
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
        # P472-03 batch 4: attribute the audit event to the caller's verified tenant;
        # with no tenant it was written under the shared "default-tenant".
        tenant_id=tenant_id,
        details={
            "source_type": source_type, "source_id": source_id, "knowledge_version": knowledge_version,
            "model_version": model_version, "workflow_version": workflow_version,
            # P472-03 B5.4: seal the ledger CONTENT into the hash-chained event, so an
            # edit of the evidence (or of anything else in the row) is detectable.
            EVIDENCE_DIGEST_KEY: evidence_digest(row),
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


def _readable_by(db: Session, entry: EvidenceLedgerEntry, caller_tenant_id: str) -> bool:
    """P472-03 B6.2 read gate (fail closed, no migration; GD-7 unsigned).

    The ledger has no tenant column. An entry is served only when its
    hash-chained audit trail names exactly one real tenant and that tenant is
    the caller's verified tenant. Another tenant's entry, and any legacy entry
    whose ownership cannot be proven (no audit event, only ``default-tenant``,
    several tenants), is refused to every tenant — quarantined, not attributed.
    """
    from app.services.guardianx_ledger_ownership import audit_owner_tenant

    return bool(caller_tenant_id) and audit_owner_tenant(db, entry.id) == caller_tenant_id


def _get_readable_or_404(db: Session, entry_id: int, caller_tenant_id: str) -> EvidenceLedgerEntry:
    row = db.query(EvidenceLedgerEntry).filter(EvidenceLedgerEntry.id == entry_id).first()
    if row is None or not _readable_by(db, row, caller_tenant_id):
        raise UnknownEvidenceLedgerEntryError(f"Evidence ledger entry {entry_id} not found.")
    return row


def get_entry(db: Session, entry_id: int, caller_tenant_id: str) -> dict:
    return _to_dict(_get_readable_or_404(db, entry_id, caller_tenant_id))


def list_entries_for_source(db: Session, source_type: str, source_id: str, caller_tenant_id: str) -> list[dict]:
    rows = (
        db.query(EvidenceLedgerEntry)
        .filter(EvidenceLedgerEntry.source_type == source_type, EvidenceLedgerEntry.source_id == source_id)
        .order_by(EvidenceLedgerEntry.recorded_at.asc())
        .all()
    )
    return [_to_dict(r) for r in rows if _readable_by(db, r, caller_tenant_id)]


def entry_integrity(db: Session, entry: EvidenceLedgerEntry) -> dict:
    """Integrity of one ledger row (P472-03 B5.4).

    ``verified`` is true only when ALL of these hold:

    * the audit hash chain of the entry is unbroken;
    * the row's ``digital_signature`` equals the event hash of its recording
      event (before B5.4 this was never compared, so a rewritten signature
      still "verified");
    * the row's content digest equals the digest sealed into that event (before
      B5.4 the content was not sealed at all, so edited evidence still
      "verified").

    A row recorded before B5.4 has no sealed digest: its content cannot be
    verified, so it is reported as ``legacy_unsealed_evidence`` and does NOT
    verify (fail closed).
    """
    chain = verify_audit_chain(db, resource_type=_RESOURCE_TYPE, resource_id=str(entry.id))
    recording = (db.query(AuditLog)
                 .filter(AuditLog.resource_type == _RESOURCE_TYPE, AuditLog.resource_id == str(entry.id),
                         AuditLog.action_type == "guardianx.evidence_recorded")
                 .order_by(AuditLog.id.asc()).first())
    details = {}
    if recording is not None:
        details = recording.details if isinstance(recording.details, dict) else json.loads(recording.details or "{}")
    signature_matches = bool(recording is not None and entry.digital_signature
                             and entry.digital_signature == str(details.get("event_hash", "")))
    sealed = details.get(EVIDENCE_DIGEST_KEY)
    digest_matches = None if sealed is None else (sealed == evidence_digest(entry))
    if not chain.get("verified"):
        integrity = "audit_chain_broken"
    elif recording is None:
        integrity = "no_recording_event"
    elif not signature_matches:
        integrity = "signature_mismatch"
    elif digest_matches is None:
        integrity = "legacy_unsealed_evidence"
    elif not digest_matches:
        integrity = "evidence_mismatch"
    else:
        integrity = "intact"
    return {
        **chain,
        "chain_verified": bool(chain.get("verified")),
        "signature_matches": signature_matches,
        "evidence_digest_matches": digest_matches,
        "integrity": integrity,
        "verified": integrity == "intact",
    }


def verify_entry(db: Session, entry_id: int, caller_tenant_id: str) -> dict:
    """Confirms the entry's content and `digital_signature` still match an
    unbroken hash chain -- proof the ledger hasn't been tampered with. Only the
    owning tenant may verify (B6.2; GD-2: verification stays inside the tenant)."""
    return entry_integrity(db, _get_readable_or_404(db, entry_id, caller_tenant_id))
