# P472-03 B6.2 — GuardianX Evidence Ledger: Fail-Closed Read Gate (v1)

**Issue #188 · PR #181 (DRAFT).** **GD-7 is NOT signed.** No schema change, no ownership/tenant attribution
written, no audit hash changed, no migration executed. The ownership ADR and quarantine plan in
`p472-03-b54-guardianx-ledger-adr-v1.md` remain proposals.

## Trace (append → read → verify → replay)
| Path | Consumer | Before | Now |
|---|---|---|---|
| `POST /evidence` | ledger append + hash-chained audit event (tenant = verified tenant since Batch 4; content sealed since B5.4) | unchanged | unchanged |
| `GET /evidence/{id}` | API | any tenant | **owner tenant only**, else 404 |
| `GET /evidence?source_type=&source_id=` | API | every tenant's entries for the key | **only entries owned by the caller** |
| `GET /evidence/{id}/verify` | API | any tenant | **owner tenant only** (GD-2 consistency), else 404 |
| `GET /audit-replay/inspections/{id}` | replay service (inspection already tenant-scoped, AW-08) | embedded all tenants' ledger entries for the inspection id | embeds only the caller's |
| `GET /audit-replay/workflow-executions/{id}` | replay service | **returned another tenant's execution** (decision path, log) and embedded all tenants' entries | execution looked up **by verified tenant** (B6.2b; reproduced 200 → now 404); embeds only the caller's entries |
| `GET /audit-replay/rules/{id}` | replay service | **returned another tenant's rule logic** | looked up by verified tenant (B6.2b; reproduced 200 → 404) |
| `GET /audit-replay/recommendations?source_type=&source_id=` | replay service | **embedded another tenant's evidence and reviewer email** (reproduced on `e2173c2`; new test) | embeds only the caller's |
| export | none exists for the ledger | — | — |

**Ownership for the gate** = `guardianx_ledger_ownership.audit_owner_tenant`: the single real tenant on the
entry's hash-chained audit trail. Entries with no audit event, only `default-tenant`/no tenant (pre-Batch-4
writes) or several tenants are readable by **no tenant** (quarantined in place, fail closed). Integrity is not
part of the gate, so a tampered entry stays visible to its owner and `verify` reports it.

Both GD-7 options (tenant-owned, or platform-wide with a privileged reader) deny tenant users cross-tenant
reads; this gate is that common floor. **Operational impact:** legacy entries become unreadable through the
tenant APIs until GD-7 decides their fate.

## Reproduction and results
* Before (`e2173c2`): `TestOpenOwnershipFindings --runxfail` → 5 failed on their own assertions; replay
  embedding test → failed (`tenant-a-evidence` in tenant B's replay).
* After: GD-7 file + existing GuardianX suite **48 passed**; all replay/ledger suites **204 passed**.
  5 markers removed with assertions **unchanged** → RB-T24…RB-T28 are **author conversions** (release
  blockers pending non-author disposition). New controls: owner read/list/verify, multi-membership
  selection, no membership (403), legacy pooled entry unreadable by anyone, tampered own entry reported,
  write claiming another tenant (403).

## Still pending GD-7 (not implemented)
Tenant column + attribution migration (dry-run classifier only), platform-security reader role, retention,
release of quarantined legacy entries, source-object ownership checks on write.
