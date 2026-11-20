"""GuardianX source-object write authorization (P472-03 Batch 7, GD7-05 follow-up).

The evidence ledger and the explainability records reference the AI output they
describe by a client-chosen ``source_type`` / ``source_id`` pair. Until Batch 7 a
caller could write under any pair, including another tenant's inspection; the
write persisted and (for explanations) surfaced in the victim's audit replay.

This module decides, before a write, whether the verified tenant may write under
a source. It implements only what existing authorization policy already settles
and fails closed elsewhere:

1. **Owned source types** — the source is a tenant-owned row whose ownership is
   already enforced on reads (inspection: AW-08c; workflow execution: B6.2b). The
   row must exist **and** belong to the caller's verified tenant; otherwise the
   write is refused exactly like a missing source (404, no existence oracle).

2. **Ownerless source types** (no table records the source, e.g. on-the-fly
   ``capa_suggestion`` / ``rca_suggestion`` ids, or any unregistered type) — what
   such a key means and who owns it is governance decision **GD-7 (unsigned)**.
   This module does not decide it. It only blocks the operation that is unsafe
   under every GD-7 option: writing ledger evidence into a key that already holds
   entries not provably owned by the caller (another tenant's, or legacy entries
   with no single-tenant audit trail). A key no one has used stays writable, as
   before — whether that should continue is part of GD-7 (risk R-GX-OWNERLESS-KEYS).

Explanations for ownerless keys are not checked here: explanation rows carry no
owner and no audit trail, so their ownership cannot be proven at all (open
finding GX-09 / RB-T32, pending GD-7).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.guardianx_assurance import EvidenceLedgerEntry
from app.models.inspection import Inspection
from app.models.workflow_forge import WorkflowExecution

# source_type -> (model, primary-key column, tenant column). Only types whose
# tenant ownership is already enforced elsewhere belong here; adding one is a
# reviewed change, not a configuration value.
OWNED_SOURCE_TYPES = {
    "inspection": (Inspection, Inspection.id, Inspection.tenant_id),
    "workflow_execution": (WorkflowExecution, WorkflowExecution.id, WorkflowExecution.tenant_id),
}
MAX_SOURCE_FIELD = 200


class InvalidSourceError(ValueError):
    """Empty or malformed source reference (422)."""


class SourceNotFoundError(LookupError):
    """Owned source missing or owned by another tenant — indistinguishable (404)."""


class SourceWriteRefusedError(PermissionError):
    """Ownerless key already used by another or an unprovable owner (403)."""


def _clean(source_type, source_id) -> tuple[str, str]:
    if not isinstance(source_type, str) or not isinstance(source_id, str):
        raise InvalidSourceError("source_type and source_id must be strings.")
    st, sid = source_type.strip(), source_id.strip()
    if not st or not sid or len(st) > MAX_SOURCE_FIELD or len(sid) > MAX_SOURCE_FIELD:
        raise InvalidSourceError("source_type and source_id are required (at most 200 characters).")
    return st, sid


def _require_owned_source(db: Session, source_type: str, source_id: str, tenant_id: str) -> None:
    model, pk, tenant_col = OWNED_SOURCE_TYPES[source_type]
    try:
        key = int(source_id)
    except ValueError:
        raise SourceNotFoundError("Source not found.") from None
    if db.query(model).filter(pk == key, tenant_col == tenant_id).first() is None:
        raise SourceNotFoundError("Source not found.")


def authorize_evidence_write(db: Session, source_type, source_id, tenant_id: str) -> tuple[str, str]:
    """Return the cleaned (source_type, source_id) the verified tenant may write evidence under."""
    if not (tenant_id or "").strip():
        raise SourceWriteRefusedError("No verified tenant for this request.")
    st, sid = _clean(source_type, source_id)
    if st in OWNED_SOURCE_TYPES:
        _require_owned_source(db, st, sid, tenant_id)
        return st, sid
    from app.services.guardianx_ledger_ownership import audit_owner_tenant
    existing = db.query(EvidenceLedgerEntry.id).filter(EvidenceLedgerEntry.source_type == st,
                                                       EvidenceLedgerEntry.source_id == sid).all()
    if any(audit_owner_tenant(db, entry_id) != tenant_id for (entry_id,) in existing):
        raise SourceWriteRefusedError("Recording evidence for this source is not permitted.")
    return st, sid


def authorize_explanation_write(db: Session, source_type, source_id, tenant_id: str) -> tuple[str, str]:
    """Owned source types only (see module docstring); ownerless keys pass through unchanged."""
    if not (tenant_id or "").strip():
        raise SourceWriteRefusedError("No verified tenant for this request.")
    st, sid = _clean(source_type, source_id)
    if st in OWNED_SOURCE_TYPES:
        _require_owned_source(db, st, sid, tenant_id)
    return st, sid
