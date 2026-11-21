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

3. **Explanations** (Batch 8, RB-T32 / GX-11..GX-14) — explanation rows have no
   owner column; adding one would pre-empt GD-7 (Option T vs P). Instead each
   explanation is attributed exactly like a ledger entry since B6.2: by the
   single real tenant on its hash-chained audit trail. New explanations and
   human overrides record an audit event under the writer's verified tenant.
   A row with no provable owner (written before Batch 8, or with a conflicting
   trail) is readable and writable by **no tenant** — quarantined, never
   re-attributed (GD-7 / CLIN-1 decide its release).

An ownerless key is treated as one namespace across both artifacts: a write
(ledger or explanation) into a key that already holds a ledger entry or an
explanation not provably the caller's is refused. This is the rule-2 floor
extended to explanations; it does not decide what an ownerless key means.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.guardianx_assurance import AIExplainabilityRecord, EvidenceLedgerEntry
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
EXPLANATION_RESOURCE_TYPE = "guardianx_explainability_record"


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
    _refuse_key_used_by_another(db, st, sid, tenant_id, "Recording evidence for this source is not permitted.")
    return st, sid


def authorize_explanation_write(db: Session, source_type, source_id, tenant_id: str) -> tuple[str, str]:
    """Return the cleaned (source_type, source_id) the verified tenant may explain (rules 1 and 3)."""
    if not (tenant_id or "").strip():
        raise SourceWriteRefusedError("No verified tenant for this request.")
    st, sid = _clean(source_type, source_id)
    if st in OWNED_SOURCE_TYPES:
        _require_owned_source(db, st, sid, tenant_id)
        return st, sid
    _refuse_key_used_by_another(db, st, sid, tenant_id, "Explaining this source is not permitted.")
    return st, sid


def explanation_owner(db: Session, record_id: int) -> str | None:
    """The single real tenant on an explanation's audit trail, or None (quarantined)."""
    from app.services.guardianx_ledger_ownership import audit_trail_owner
    return audit_trail_owner(db, EXPLANATION_RESOURCE_TYPE, record_id)


def explanation_readable_by(db: Session, record_id: int, tenant_id: str) -> bool:
    """Only the provable owner may read or amend an explanation. No tenant -> no access."""
    tenant = (tenant_id or "").strip()
    return bool(tenant) and explanation_owner(db, record_id) == tenant


def _refuse_key_used_by_another(db: Session, st: str, sid: str, tenant_id: str, message: str) -> None:
    from app.services.guardianx_ledger_ownership import audit_owner_tenant
    ledger = db.query(EvidenceLedgerEntry.id).filter(EvidenceLedgerEntry.source_type == st,
                                                     EvidenceLedgerEntry.source_id == sid).all()
    if any(audit_owner_tenant(db, entry_id) != tenant_id for (entry_id,) in ledger):
        raise SourceWriteRefusedError(message)
    explanations = db.query(AIExplainabilityRecord.id).filter(AIExplainabilityRecord.source_type == st,
                                                              AIExplainabilityRecord.source_id == sid).all()
    if any(explanation_owner(db, record_id) != tenant_id for (record_id,) in explanations):
        raise SourceWriteRefusedError(message)
