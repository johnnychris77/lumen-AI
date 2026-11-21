# P472-03 — Independent Review Packages v2 (Batch 6) — RB-T01 … RB-T28

**PR #181 (DRAFT) · Issue #188** · extends `p472-03-batch5-independent-review-packages-v1.md` (preserved;
packages A, B, F unchanged and still required). **Requests, not reviews. No reviewer assigned** (one
repository collaborator — the program owner — and no PR reviews; appointing reviewers is a human action).

## Package C′ — RB-T01 (now author-converted by B6.1)
1. Sweep oracle at `3c8d347` (before): 1 route with AW-04 (`GET /api/genesis-ai/manufacturer-updates`).
2. Sweep at `38251e6` and later (after): 0 routes. Commands as in package B (SQLite and `--sweep postgres`).
3. Read `refuse_other_tenants(...)` in `get_manufacturer_updates`: the filter now refuses another tenant
   (403) rather than binding it. Judge whether the oracle's silence reflects a real fix.

## Package D′ — RB-T15 … RB-T23 (Genesis; author-converted by B6.1 `38251e6`)
* Before: `git checkout 9f2b6e3 && pytest tests/test_p472_03_batch5_genesis_gd6.py::TestOpenFindings --runxfail`
  → 9 failed on their own assertions.
* After: `git checkout 38251e6 && pytest tests/test_p472_03_batch5_genesis_gd6.py` → 21 passed.
* Assertion check: `git diff 9f2b6e3 38251e6 -- backend/tests/test_p472_03_batch5_genesis_gd6.py` — marker lines
  removed; **GD6-04 (RB-T18) amended** (request now 403) — decide whether the amendment preserves the intent.
* Behaviour review: `p472-03-b61-genesis-fail-closed-v1.md`; confirm no new publisher/curator was designated.

## Package E′ — RB-T24 … RB-T28 (GuardianX; author-converted by B6.2 `3f479d9`)
* Before: `git checkout e2173c2 && pytest tests/test_p472_03_batch5_guardianx_gd7.py::TestOpenOwnershipFindings --runxfail`
  → 5 failed on their own assertions; `TestB62ReplayEmbedding` (add the test file from `3f479d9`) fails.
* After: `git checkout 3f479d9 && pytest tests/test_p472_03_batch5_guardianx_gd7.py` → all pass.
* Confirm: no schema change, no tenant attribution written, audit hashes untouched; legacy entries
  quarantined (unreadable). Review `audit_owner_tenant` (ownership from the hash-chained audit trail).

## Package G — Batch 6 functional compatibility (B6.3)
* Browser E2E `frontend/tests/e2e/tenantContext.e2e.mjs` (single/multi/no-membership/forged/cross-tenant).
* PG16: `test_p472_03_batch5_{tenant_context,manufacturer_iam,auth_role_lookup}.py`, AW-07, login suites.
* Alembic guarded downgrade of `b5a2c7e19d40` with an expired membership present.

## Reviewer roles needed (none assigned)
Tenant authorization (packages A, B, C′) · Genesis/GD-6 (D′) · ledger/data migration and GD-7 (E′) ·
manufacturer IAM / GD-9 (package F) · frontend/API owner (G, tenant-context ADR) · clinical governance
(CLIN-1) · authentication owner (AUTH-1/2).
