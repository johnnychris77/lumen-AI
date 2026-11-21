# Governance Decision Register (v4 — Batch 5)

**PR #181 (DRAFT) · Issue #187** · supersedes v3 (preserved). **No decision below is signed.** Only an
authorized, accountable owner records identity, timestamp and decision, and only when they personally make
it. The author cannot sign, and no named owner has been identified from the repository.

| ID | Question | Current behaviour (safe default) | Packet | Accountable role | Decision |
|---|---|---|---|---|---|
| GD-1 … GD-4 | as in v2/v3 | unchanged | v2 | per v2 | **PENDING** |
| GD-5 | Tenant selection only via `X-Tenant-Id`, or also by repeating `tenant_id`? | claims must equal the verified tenant; the B5.1 web client sends the header **and** repeats it where a route requires the parameter | `p472-03-tenant-context-adr-v1.md` | API / product owner | **PENDING** |
| GD-6 | Genesis feed: visibility of unpublished updates; who may publish/reject; identity disclosure | unchanged open model; 9 exposures pinned as tripwires RB-T15…T23; RB-T01 open | `p472-03-b53-gd6-decision-packet-v1.md` | network / clinical governance | **PENDING** |
| GD-7 | GuardianX ledger platform-wide or tenant-owned; attribution of history | ledger unscoped (5 tripwires RB-T24…T28); content sealing **implemented**; ownership classifier dry-run only | `p472-03-b54-guardianx-ledger-adr-v1.md` | platform-security owner | **PENDING** |
| GD-8 | Commercial platform-wide health view: should it exist, for whom? | API: PA-1 class only, logged. **UI no longer offers it** (B5.1) | tenant-context ADR §Decision 4 | commercial + security owner | **PENDING** |
| GD-9 | Manufacturer IAM: who may grant/revoke, identity proofing, role catalogue, expiry, approval, API exposure, manufacturer vs hospital identity | grants **gated closed**; revocation service (no route) + expiry implemented | `p472-03-b52-manufacturer-iam-lifecycle-v1.md` | IAM owner | **PENDING** |
| AUTH-1 | Enable or remove legacy `users`-table password login? | disabled, logged (never worked against the canonical schema) | `p472-03-b55-postgres-auth-defect-report-v1.md` | authentication owner | **PENDING** |
| AUTH-2 | Accept that `users.role` now applies when no role assignment exists (B5.5 contract change); inventory existing `users.role` values before deploy | applied (documented resolution order) | same | authentication owner | **PENDING** |
| PA-1 | Platform-admin / dev-token cross-tenant exception | unchanged, logged | routing packet B | platform-security owner | **PENDING** |
| CLIN-1 | Clinical approval of legacy attribution (GD-3 quarantine, GD-7 quarantine) | quarantined, fail closed | GD-3 checklist v2; GD-7 ADR §5 | clinical operations owner | **PENDING** |

**No release-governance decision is recorded. Disposition: HOLD / NO-GO.**
