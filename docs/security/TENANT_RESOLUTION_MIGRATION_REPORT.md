# Tenant Resolution Migration Report

## Root cause

`app/deps._load_tenant_memberships` built `TenantMembershipView(tenant_name=r.tenant_name,
role_name=r.role_name)` — columns that exist only on a **dead duplicate model**, not
on the live `app.db.models.TenantMembership` (`role`, no `tenant_name`). The read
`AttributeError`'d into a broad `except: return ()`, so **every principal carried
empty tenant memberships**, and `resolve_verified_tenant` fail-closed-403'd every
non-platform-admin on membership-scoped routes.

## Why the previous fix regressed 62 tests

Correcting the loader made principals carry real memberships. That surfaced a
**test-isolation defect**: the test DB is a shared SQLite *file* that is never
truncated between tests, and dozens of tests seed
`TenantMembership(user_email="{role}@local.dev", tenant_id=<random>, ...)` using the
same dev identities that dev-token principals resolve to. Those rows leaked into
later tests, so an `operator` whose data lived in `default-tenant` suddenly carried
memberships in a dozen random tenants → routes scoped to the wrong tenant → 404s.

**The routes were never the problem.** No route migration was required — they resolve
tenant correctly once the principal carries real memberships.

## What changed

1. **Loader** (`app/deps.py`): read the live model directly (`tenant_id`, `role`);
   no phantom fields. Operational load failures fail closed to no memberships **and
   are logged** (not silently swallowed), so schema/programming errors are visible.
2. **Test isolation** (`tests/conftest.py`): autouse per-test `DELETE FROM
   tenant_memberships`. Every test that needs a membership seeds its own (all seeds
   are per-test helpers), eliminating cross-test principal pollution.
3. **Contract tests** (`tests/test_tenant_resolution_contract.py`): executable
   spec of cases A–G.
4. **Docs:** map, contract, model, ADR, isolation matrix, this report.

Retained from the prior PR (#138): tenant-admin API repaired to the live model;
dead duplicate model removed; startup membership bootstrap (#137).

## Results

- **Full SQLite suite (fresh DB): 3760 passed, 2 skipped, 0 failed.** The 3
  previously pre-existing `test_sentinel_orchestration` **order/session-dependent
  flakes** (`test_no_signal_below_threshold`,
  `test_insufficient_history_not_flagged`,
  `test_no_duplicate_alerts_for_same_signal`) are now **fixed** (see the sentinel
  flake note below). They were rooted in broad `inspections`/`findings`
  accumulation on the shared file DB, **not** tenant resolution.
- The 62 tenant-pollution regressions from the previous attempt are **fixed**.
- Isolation/privilege suites all green (see the test matrix).
- PostgreSQL suite: not run locally (no server in this environment); relies on CI.

## Migration approach vs. the planned one

The task anticipated a feature-gated, domain-by-domain route migration
(`TENANT_RESOLUTION_V2`). Investigation showed that was **unnecessary**: the defect
was the loader + test pollution, not route coupling, so a controlled loader fix +
test isolation resolves it cleanly without a flag or per-route changes. No feature
flag was introduced (nothing to gate); no temporary compatibility layer exists to
remove.

## Remaining technical debt (follow-ups, not blockers)

1. **Pre-existing sentinel order-flakes** (3 tests) — **fixed.** Root cause: the
   test DB is a shared SQLite *file* never reset between pytest *sessions*, so
   `inspections`/`findings` accumulate across runs. Three negative-assertion tests
   hardcoded a fixed zone/barcode (e.g. `unique_zone_xyz`, `twin-insufficient-001`)
   that collided with **their own rows from previous runs** — after seven runs,
   seven accumulated findings in the "unique" zone tripped the detection threshold,
   inverting the assertion. Fixed by giving each of those tests a per-run-unique
   identifier (`uuid4`), so every negative assertion depends only on the rows the
   test itself seeds — robust under any order and independent of prior runs. No
   production code changed; no broad table truncation needed. The deeper
   shared-file-DB pattern (item 4) is unchanged.
2. **Platform-admin vs tenant-admin separation** — see the ADR. Global `admin` is
   cross-tenant by design; a confined tenant-admin identity is deferred.
3. **DB constraint** — add a composite unique index on
   `tenant_memberships(user_email, tenant_id)`; today duplicates are prevented only
   in code.
4. **Broader test isolation** — the shared-file-DB-without-reset pattern will keep
   producing order-flakes; a per-test transaction/rollback harness is the long-term
   fix.

## Rollback

Revert the commits. `_load_tenant_memberships` returns to the empty-membership
behavior; the conftest truncation is inert without the loader change. No schema
migration to unwind.
