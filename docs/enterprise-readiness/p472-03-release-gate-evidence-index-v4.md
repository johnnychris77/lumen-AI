# P472-03 — Release Gate Evidence Index (v4 — Batch 5)

**PR #181 (DRAFT) · Issue #187** · supersedes v3 (preserved). **Overall gate: NO-GO.**
A green CI job containing an unresolved security xfail is **not** a passing security gate.

## Batch 5 commits (baseline `7cead8a`)
`6247d6f` B5.0 evidence freeze · `189094d` B5.1 tenant context · `e226ee2`, `06394c0` B5.5 auth role lookup ·
`de80b7b` B5.2 manufacturer lifecycle · `c677590` B5.3 GD-6 tripwires · `3c8d347` B5.4 ledger integrity +
GD-7 tripwires (**final code SHA of Batch 5**) · this documentation commit.

## Verification on `3c8d347`
| Check | Command / source | Result |
|---|---|---|
| Full suite, SQLite (local) | `cd backend && python -m pytest tests/ -q -rsx` (fresh SQLite) | **9190 passed, 3 skipped, 15 xfailed, 0 failed, 0 xpassed** (16 m 33 s) |
| Full suite, SQLite (CI) | run `44633695173`, job `135946704078` | job *success*: **9190 passed, 3 skipped, 15 xfailed** (19 m 15 s) — **not a passing security gate** (15 security xfails) |
| Full suite, PostgreSQL 16.15 (local) | same, fresh PG16 database | **9191 passed, 2 skipped, 15 xfailed, 0 failed, 0 xpassed** (27 m 39 s); server log: 1 `column "username"` error = the test's deliberate schema probe |
| Full suite, PostgreSQL 16 (CI) | run `44633695173`, job `135946704039` | **IN PROGRESS at the time of writing** — not assumed |
| Skipped | both | `test_benchmarking.py:83` (no hospitals), `test_p10_digital_twin.py:317` (no open alerts); SQLite only: `test_p472_trusted_inference_provenance.py:788` (PG-only Alembic) |
| Expected failures (15) | both | RB-T01 `test_no_route_exhibits[AW-04]`; RB-T15…T23 `test_p472_03_batch5_genesis_gd6.py::TestOpenFindings` ×9; RB-T24…T28 `test_p472_03_batch5_guardianx_gd7.py::TestOpenOwnershipFindings` ×5 |
| Sweep, SQLite | `tenant_isolation_matrix.py --sweep sqlite --workdir <fresh>` | **1,913 routes** (+1: `GET /api/auth/tenants`); **1** with a finding (`GET /api/genesis-ai/manufacturer-updates`, AW-04); 0 foreign-write routes |
| Sweep, PostgreSQL 16.15 | `--sweep postgres --postgres-url …` | 1,913 routes; **1** finding — identical; `unstable: {}` |
| Register / matrix | rebuilt from both sweeps | 1 entry (unchanged); matrix + CSV regenerated |
| Alembic, PG16 fresh DB | `alembic heads`; `upgrade head`; `downgrade -1`; `upgrade head` | single head **`b5a2c7e19d40`**; all steps OK; guarded downgrade refuses while lifecycle data exists (verified with an expired row) |
| Ruff | `ruff check backend/app backend/tests` | All checks passed (CI job `135946704242` success) |
| Frontend tests | `npm test` | **48/48** (16 new tenant-context tests) |
| Frontend build | `npm run build` | built (CI `135946703984`, `135946704370` success) |
| Browser E2E (Chromium, real login, real backend) | `frontend/tests/e2e/tenantContext.e2e.mjs` | **6/6** on `3c8d347`; **0/6** on the baseline frontend `7cead8a` (reproduction: `403 …?tenant_id=default-tenant`) |
| CI security / quality | run `44633695173` + siblings | secret scan ×2, ruff, frontend ×2, dependency audit, security hardening, security-and-lint, compliance, core CI, enterprise quality gate: **11/11 success** |

## Gates
| Gate | Status |
|---|---|
| G1 tenant isolation (resolvers) | technically remediated; **PENDING** review |
| G2 residual register | **FAIL / OPEN** — 1 route (RB-T01) |
| G3 AW-07 manufacturer identity | lifecycle partly remediated; **OPEN** (GD-9) |
| G4 AW-08 | **PENDING** review |
| G5 GD-3 | **PENDING** review |
| G6 PA-1 | **PENDING** decision |
| G7 GD-1…GD-9, AUTH-1/2, CLIN-1 | **PENDING** (none signed) |
| G8 clinical workflow | **PENDING** |
| G9 frontend contract | technically remediated (browser 6/6); **PENDING** frontend/API owner review |
| G10 CI security/lint/quality | PASS on `3c8d347` (11/11) |
| G11 CI backend suites | SQLite completed 0 failed — **NOT PASS** (15 security xfails); PG16 **in progress** |
| G12 historical access | **BLOCKED** |
| G13 independent review | **PENDING** — no reviewer identifiable (1 collaborator, 0 reviews) |
| G14 tripwires | **28 release blockers** (15 failing, 13 converted), 0 dispositioned |
| G15 release decision | **PENDING** |

**Disposition: PR #181 DRAFT · P472-03 OPEN · HOLD / NO-GO.**
