# LPR-DIR-014 — Audit & Evidence Security (Phase 3)

**Basis:** code inspection + `test_audit_chain_verification`,
`test_evidence_authorization_baseline` (passed) at `f889d95`.

## Audit integrity (verified)

| Property | Implementation | Evidence |
|---|---|---|
| Single writer | `enterprise_audit_service.record_enterprise_audit_event` | `services/enterprise_audit_service.py` |
| Hash chaining | Each event chains to the prior → tamper-evident | `test_audit_chain_verification` |
| Append-only | No update/delete API on audit events | Phase 1 data-authority |
| Tenant scope | Events tenant-scoped | isolation tests |
| Deprecated shim | `app.audit.log_audit_event` emits `DeprecationWarning`, delegates to the hash-chained writer (no competing SoR) | runtime warning observed |

**Attempted:** audit bypass / history rewriting — the append-only + hash-chain
design makes silent rewriting detectable; the chain-verification endpoint requires
admin and returns a validity result. No rewrite path surfaced.

## Evidence integrity (verified)

| Property | Implementation | Evidence |
|---|---|---|
| Checksummed bundles | Evidence packages carry checksums | Phase 1 |
| Authorization | Evidence generation/access is authorized | `test_evidence_authorization_baseline` |
| Not-promoted-on-incomplete | Incomplete bundle is quarantined, not promoted | failure-arch |
| Lineage | Generated from governed records only | data-authority |

**Attempted:** evidence mutation / report manipulation — evidence is checksummed
and audit-chain-immutable; reports are generated from governed records (not editable
in place). No mutation path surfaced.

## Finding — SEC-AUD-01 (MEDIUM) — audit write not atomic with the business write
(= AR-16 / boundary 11). Several paths commit business data before the audit insert;
a failed audit write leaves committed data without a chain entry. The chain itself
remains tamper-evident, but the **completeness** guarantee ("every governed write is
audited") is not transactionally enforced. **Mitigation:** wrap write+audit in one
transaction or use a transactional outbox; surface audit-write failure. This is the
only audit/evidence security gap; it weakens, but does not break, immutability.

## Assessment
Audit and evidence integrity are **strong and test-verified**: hash-chained,
append-only, tamper-evident audit with a single writer; checksummed,
authorization-gated, immutable evidence. The one gap (SEC-AUD-01) is a
transaction-atomicity completeness issue, not a bypass or mutation path.

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| SEC-AUD-01 | MEDIUM | Audit write not atomic with business write (AR-16); completeness not transactionally guaranteed |
| SEC-AUD-02 | OBSERVATION | Retire deprecated `app.audit` shim (second call path; carryover B-01) |
