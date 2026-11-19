# P472-03 — Release Gate Evidence Index (v3 — Batch 4)

**PR #181 (DRAFT)** · **Issue #186** · supersedes `p472-03-release-gate-evidence-index-v2.md` (preserved).
Legend: **PASS** (evidence recorded) · **PENDING** (awaiting a run or an independent human action) ·
**BLOCKED** · **FAIL / OPEN**. A technical PASS is not an independent review. **Overall gate: NO-GO.**

**Tripwire rule.** An expected security-tripwire failure (strict `xfail`) is **not** a successful check,
even inside a CI job whose conclusion is *success*; and a tripwire converted by the author is not a closed
finding. All such items are release blockers listed in `p472-03-security-tripwire-disposition-v1.md`
(RB-T01…RB-T14) until a non-author reviewer records a disposition.

## Verification evidence on the final code SHA `d62dddc`
(`d62dddc` and `7605885` are documentation-only over `c826fcc`; the backend code is identical.)

| Check | Command / source | Result |
|---|---|---|
| Full suite, SQLite (CI) | run `44603433105`, job `135840665336` | job *success*: **9111 passed, 3 skipped, 1 xfailed, 0 failed** (18 m 20 s). The xfail is **RB-T01** — an open finding, **not a pass**. |
| Full suite, PostgreSQL 16 (CI) | run `44603433105`, job `135840665397` | job *success*. The pytest summary line is **not extractable**: the log API returns at most the last 5,000 lines and all of them are the PostgreSQL service-container dump. Counts are taken from the local run below. |
| Full suite, PostgreSQL 16.15 (local) | `cd backend && DATABASE_URL=postgresql://…/b4_full_pg python -m pytest tests/ -q` | **9112 passed, 2 skipped, 1 xfailed, 0 failed** (28 m 11 s). Xfail = **RB-T01**. The Alembic-chain test runs here (skipped on SQLite). Skips are data-dependent (see disposition register §C). |
| Full suite, SQLite (local) | `c826fcc`, same code | 9111 passed, 3 skipped, 1 xfailed, 0 failed |
| Skip / xfail identification | `-rsx` re-run of the affected files on both backends | SQLite: Alembic (PG-only), `test_benchmarking.py:83`, `test_p10_digital_twin.py:317`; xfail `test_no_route_exhibits[AW-04]`. PG16: xfail identical; `test_benchmarking.py:83` skipped; the second full-run skip is order/data-dependent and was not reproduced in isolation (full run was not executed with `-rs`). |
| Tripwire file integrity | `git diff 4fdac4c d62dddc -- tests/test_p472_03_application_wide_findings.py` | only `@_finding` marker lines and comments changed; no assertion, fixture or request changed |
| Application-wide sweep, SQLite | `scripts/tenant_isolation_matrix.py --sweep sqlite` (`c826fcc`) | 1,912 routes; **1** with a finding (`GET /api/genesis-ai/manufacturer-updates`, AW-04) |
| Application-wide sweep, PostgreSQL 16.15 | `--sweep postgres` (scratch schemas) | 1,912 routes; **1** with a finding — identical to SQLite |
| Findings register | rebuilt from both sweeps (`--write-register --also`) | 1 entry; `unstable: {}`; sweeps `[sqlite, postgresql]` |
| Alembic chain, PostgreSQL 16 | fresh DB: `alembic heads`; `upgrade head`; `downgrade -1`; `upgrade head` | single head `e7c2a9f04b18`; all steps succeeded; plus the in-suite Alembic test passed on PG16 |
| Ruff | `ruff check backend/app backend/tests` | All checks passed (local; CI job `135840664849` success) |
| Frontend build | `npm --prefix frontend run build` | built (local; CI `135840665300`, `135840664750` success) — **build success does not cover R-FRONTEND (G9)** |
| CI security & quality gates | run `44603433105` + sibling runs on `d62dddc` | secret scan ×2, ruff, frontend build ×2, compliance, security-and-lint, security hardening, dependency audit (report-only), core CI, enterprise quality gate: **11/11 success** |
| PG16 server log (CI) | service-container dump in job `135840665397` | 2,450 × `column "username" does not exist` from `app/routers/auth_simple.py` raw-SQL role/login lookups against the ORM `users` table (which has `email`); exceptions are swallowed and the role falls back to `viewer` (fail-safe). **Pre-existing** (file unchanged in P472-03); recorded as R-PG-USERS, not fixed in this batch. Also 83 × `database "lumenai" does not exist` (test-harness probe) and 2 unique-constraint violations exercised by tests. |

## Gates
| Gate | Criterion | Status |
|---|---|---|
| G1 | Tenant isolation — verified resolvers (Batches 1–4) | Technically remediated (sweep: 1 route); **PENDING** independent review |
| G2 | Residual register (was 186 routes) | **FAIL / OPEN** — 1 route (GD-6); tripwire RB-T01 still fails |
| G3 | AW-07 manufacturer identity | Authorization remediated; **OPEN** provisioning/revocation workflow + IAM review |
| G4 | AW-08 object-level | Technically re-verified; **PENDING** review (RB-T09…T11) |
| G5 | GD-3 floor + migration | **PENDING** review |
| G6 | PA-1 platform-admin / dev-token exception | **PENDING** governance decision |
| G7 | GD-1 … GD-8 | **PENDING** (none signed) |
| G8 | Clinical workflow / legacy attribution | **PENDING** clinical owner |
| G9 | Frontend contract impact (R-FRONTEND: AccreditationConsole refused for real tenants; no tenant header sent) | **FAIL / OPEN** — release-blocking |
| G10 | CI security / lint / compliance / quality | PASS on `d62dddc` (11/11) |
| G11 | CI backend suites (SQLite, PostgreSQL 16) on the final SHA | Completed, 0 failed — **NOT PASS**: both contain the expected-failure tripwire RB-T01 |
| G12 | Historical access investigation | **BLOCKED** (needs authorization; no production access) |
| G13 | Independent human security review | **PENDING** — every routing slot UNASSIGNED |
| G14 | Tripwire dispositions RB-T01…RB-T14 | **PENDING** — 14 release blockers, none dispositioned |
| G15 | Authorized release decision | **PENDING** — not recorded |

## Determination
G2, G9 and G11 are not passing; G14 has 14 undispositioned release blockers; no independent review or
release decision is recorded.
**Disposition: PR #181 DRAFT · P472-03 OPEN · release HOLD / NO-GO.**
