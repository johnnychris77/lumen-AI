"""GuardianX evidence-ledger ownership classification — READ-ONLY dry run (P472-03 B5.4, GD-7).

The ledger (``guardianx_evidence_ledger_entries``) has no tenant column. Whether
it becomes tenant-owned is governance decision GD-7 (unsigned). If it does, an
approved migration needs to know, for every historical row, whether its owner
can be established WITHOUT guessing. This module answers that and nothing else:

* ``attributable`` — exactly one real tenant appears on the entry's audit trail,
  the audit hash chain verifies, and the ledger row still matches it;
* ``quarantine`` — anything else: no audit event, only the shared
  ``default-tenant`` / no tenant (pre-Batch-4 writes), several tenants, or an
  integrity failure. Quarantined rows must not be attributed by any migration.

It performs no writes and attributes nothing (asserted by the tests).
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.guardianx_assurance import EvidenceLedgerEntry

RESOURCE_TYPE = "guardianx_evidence_ledger_entry"
UNATTRIBUTED_TENANTS = frozenset({"", "default-tenant"})


def _details(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}


def audit_trail_owner(db: Session, resource_type: str, resource_id: int | str) -> str | None:
    """The single real tenant on a resource's audit trail, or None (no event,
    only ``default-tenant``/no tenant, or several tenants). Read-only."""
    tenants = {(t or "").strip() for (t,) in db.query(AuditLog.tenant_id)
               .filter(AuditLog.resource_type == resource_type, AuditLog.resource_id == str(resource_id)).all()}
    real = tenants - UNATTRIBUTED_TENANTS
    if len(real) != 1 or tenants & UNATTRIBUTED_TENANTS:
        return None
    return next(iter(real))


def audit_owner_tenant(db: Session, entry_id: int) -> str | None:
    """The single real tenant on a ledger entry's audit trail (see
    ``audit_trail_owner``). Used by the B6.2 read gate. Integrity is reported
    separately by ``verify``."""
    return audit_trail_owner(db, RESOURCE_TYPE, entry_id)


def classify_entries(db: Session) -> list[dict]:
    from app.services.guardianx_evidence_ledger_service import entry_integrity

    results: list[dict] = []
    for entry in db.query(EvidenceLedgerEntry).order_by(EvidenceLedgerEntry.id.asc()).all():
        events = (db.query(AuditLog)
                  .filter(AuditLog.resource_type == RESOURCE_TYPE, AuditLog.resource_id == str(entry.id))
                  .order_by(AuditLog.id.asc()).all())
        base = {"entry_id": entry.id, "tenant_id": None}
        if not events:
            results.append({**base, "classification": "quarantine", "reason": "no_audit_event"})
            continue
        tenants = {(e.tenant_id or "").strip() for e in events}
        real = tenants - UNATTRIBUTED_TENANTS
        if not real:
            results.append({**base, "classification": "quarantine", "reason": "unattributed"})
            continue
        if len(real) > 1 or tenants & UNATTRIBUTED_TENANTS:
            results.append({**base, "classification": "quarantine", "reason": "conflicting_tenants"})
            continue
        if not entry_integrity(db, entry)["verified"]:
            results.append({**base, "classification": "quarantine", "reason": "integrity_failure"})
            continue
        results.append({**base, "classification": "attributable", "tenant_id": real.pop(), "reason": "verified"})
    return results
