# Project GuardianX — Evidence Ledger

LumenAI Network v5.2, Section 8.

## Append-only, real signatures — never a fabricated concept

No function in `guardianx_evidence_ledger_service.py` updates or deletes
an `EvidenceLedgerEntry` row. Every entry stores the exact fields
Section 8 names: evidence, timestamp (`recorded_at`), knowledge version,
model version, workflow version, reviewer.

## Digital Signature — a real, verifiable hash, not a placeholder

Every `record_evidence` call is paired with a real call to
`enterprise_audit_service.record_enterprise_audit_event` — the same
hash-chained, tamper-evident writer used platform-wide (added to this
codebase alongside the cross-hospital tenant-isolation security fix).
The entry's `digital_signature` column stores that audit event's real
SHA-256 `event_hash`. `verify_entry` re-runs
`audit_chain_verification_service.verify_audit_chain` against the paired
audit trail to prove the signature is still part of an unbroken chain —
if any prior event in the chain were tampered with, verification fails.

```
POST /api/guardianx/evidence
GET  /api/guardianx/evidence/{id}
GET  /api/guardianx/evidence/{id}/verify
GET  /api/guardianx/evidence?source_type=...&source_id=...
```

Nothing is deleted: there is no `DELETE` route and no service function
that removes a ledger row, by design.
