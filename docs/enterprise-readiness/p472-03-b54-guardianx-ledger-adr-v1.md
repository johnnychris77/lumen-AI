# ADR — GuardianX Evidence Ledger Ownership and Integrity (P472-03 B5.4, GD-7)

**Status:** integrity fix implemented; ownership design **PROPOSED — awaiting GD-7** (platform-security owner).
**Issue #187 · PR #181 (DRAFT).** No historical row is attributed; no migration of ownership is applied.

## 1. Inventory (code at `7cead8a`)
| Element | Fact |
|---|---|
| Table | `guardianx_evidence_ledger_entries`: `id, recorded_at, source_type, source_id, evidence_json, knowledge/model/workflow_version, reviewer, digital_signature, human_review_required, disclaimer` — **no tenant column, no FK** to the source object |
| Append | `POST /api/guardianx/evidence` (`require_tenant_roles(all)`) → `record_evidence`; paired hash-chained audit event `guardianx.evidence_recorded`, attributed to the verified tenant since Batch 4 (`4308443`) |
| Read | `GET /evidence/{id}`, `GET /evidence?source_type=&source_id=` — **unscoped** |
| Verify | `GET /evidence/{id}/verify` → `verify_audit_chain(...)` with **no** `owner_tenant_id` (GD-2 inconsistency) |
| Replay / export | none for the ledger itself (GuardianX audit replay is a separate subject, AW-08 fixed) |
| Retention | none defined; rows are never deleted by code |
| Immutability | ledger: no update/delete path in code; audit rows: ORM refuses updates (`AuditImmutabilityError`) |

## 2. Integrity defects — FIXED in Batch 5 (policy-independent)
| Defect (reproduced before the fix) | Fix |
|---|---|
| The audit event hashed source + versions but **not the evidence content**: an evidence edit still "verified" | the event now seals `evidence_sha256` over the row's canonical content |
| `verify` never compared the row's `digital_signature` with the chain: a rewritten signature still "verified" | `entry_integrity` requires chain intact **and** signature = recording event hash **and** content digest = sealed digest |
| — | rows recorded before the fix have no sealed digest → `integrity: "legacy_unsealed_evidence"`, `verified: false` (fail closed; content cannot be proven) |

Contract change: `/verify` adds `chain_verified`, `signature_matches`, `evidence_digest_matches`, `integrity`;
`verified` is now false for legacy rows and any tampered row.

## 3. Open ownership exposures — strict tripwires (GD7-01…05), release blockers
GD7-01 read by id cross-tenant · GD7-02 list by source returns other tenants' entries · GD7-03 cross-tenant
verify · GD7-04 reviewer email disclosed cross-tenant · GD7-05 another tenant can append evidence under a
victim's source key (contamination). Each verified with `--runxfail` to fail on its own assertion.

## 4. Proposed design (for GD-7; NOT implemented)
**Option T (tenant-owned, recommended least-privilege):**
1. Add `tenant_id` (nullable) and `ownership_status` (`attributed` | `quarantined`) to the ledger.
2. New rows: `tenant_id` = verified tenant at write; `ownership_status = attributed`.
3. Reads (`/{id}`, list, verify): `tenant_id = verified tenant` only; others → 404. Verification passes
   `owner_tenant_id` (GD-2 consistency).
4. `source_id` must reference an object of the caller's tenant where the source type has an owner table
   (CAPA suggestion, inspection…) — else 404; otherwise the key is namespaced by tenant.
5. `reviewer` disclosed only within the owning tenant.
6. Platform-wide reads only for a separately authorized platform-security role with purpose + audit (PA-1).

**Option P (platform-wide ledger):** keep a single ledger but restrict reads to the platform-security role,
remove tenant-user reads, and stop disclosing reviewer identities. Requires the same quarantine analysis.

## 5. Migration / backfill / quarantine plan (Option T; for approval, not applied)
1. **Dry run first** (implemented, read-only): `app.services.guardianx_ledger_ownership.classify_entries`
   classifies every historical row:
   * `attributable` — exactly one real tenant on the entry's audit trail, chain intact, signature and
     content match;
   * `quarantine` — `no_audit_event`, `unattributed` (only `default-tenant`/none: pre-Batch-4 writes),
     `conflicting_tenants`, or `integrity_failure`. Legacy rows without a sealed digest classify as
     `integrity_failure` (content unprovable) unless GD-7 accepts chain-only evidence for them.
2. Governance reviews the dry-run report (counts only; no production access by the author).
3. Migration (after GD-7): add columns; `UPDATE … SET tenant_id = <audit tenant>, ownership_status =
   'attributed'` **only** for rows the reviewed report lists as attributable; all others
   `ownership_status = 'quarantined'`, `tenant_id NULL`, readable by no tenant.
4. Quarantined rows are released only by a clinical/governance owner, row by row, with an audit event.
5. Downgrade guarded (refuse while attributed/quarantined rows exist), as in `b5a2c7e19d40`.

## 6. Evidence
`tests/test_p472_03_batch5_guardianx_gd7.py`: before — integrity tests failed (tampered content and
signature "verified"); after — SQLite 36 passed + 5 xfailed (with `test_guardianx_assurance.py`),
PostgreSQL 16.15 42 passed + 14 xfailed (with the GD-6 file). Dry-run classifier: 5 tests incl. "writes
nothing".

## 7. Decisions required (GD-7)
Option T or P; whether legacy chain-only rows may be attributed; retention period; who may read
quarantined rows; whether `source_id` must resolve to an owned object.
