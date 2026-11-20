# P472-03 — Release Gate Evidence Index (v5 — Batch 6)

**PR #181 (DRAFT) · Issue #188** · supersedes v4 (preserved). **Overall gate: NO-GO.**
A green CI job is not a passing security gate while a security finding is undispositioned. At the Batch 6
code there are **0 failing strict xfails**, but all **28 tripwires (RB-T01…RB-T28) are author conversions**.
Each one stays a release blocker until a non-author reviews and dispositions it.

## B6.0 — Batch 5 handoff (verified, not assumed)
| Item | Result on `3c8d347` |
|---|---|
| Branch SHA at start of Batch 6 | `3c8d347` (code), `9f2b6e3` (Batch 5 docs on top) |
| CI PG16, run `44633695173`, job `135946704039` | **success** (counts not retrievable: the log API returns only the last 5,000 lines, all PostgreSQL service output) |
| Local SQLite / PG16, CI SQLite | as recorded in v4: 9190/3/15 xfailed; 9191/2/15; CI 9190/3/15 — 0 failed everywhere |

## Batch 6 commits (baseline `3c8d347` / `9f2b6e3`)
| SHA | Content |
|---|---|
| `38251e6` | B6.1 Genesis fail closed (RB-T01, RB-T15…T23) |
| `e2173c2` | B6.1 doc correction (frontend caller statement) |
| `3f479d9` | B6.2 GuardianX ledger read gate (RB-T24…T28) + replay embedding |
| `00aec32` | B6.2b workflow-execution and rule replay tenant-scoped |
| `c63d398` | B6.3 E2E harness wait (network idle); no app change |
| `bc0cb94` | Registers: tripwires v3, risk v5, governance v5, review packages v2 |
| `2976b4e` | Census pin 714 → 715 (omitted after B6.1) — **final application code** |
| `e81b51d` | Matrix/register regenerated from final sweeps |
| this commit | evidence index v5, residual-risk note |

## CI failures during Batch 6 (all one cause, fixed in `2976b4e`)
`test_the_route_table_is_the_mounted_application` pinned 714 resolver-using handlers. B6.1 added
`refuse_other_tenants` to `GET /api/genesis-ai/manufacturer-updates`, which raised the count to 715. I did
not run the census test after B6.1. That was my omission.
| Commit | Job | Result |
|---|---|---|
| `3f479d9` | SQLite `135967500923` | 1 failed / 9219 passed / 3 skipped |
| `3f479d9` | PG16 `135967501020` | failure (counts not retrievable; same code as the local reproduction below) |
| `c63d398` | SQLite `135969894965`; PG16 `135969896426` | failure / failure |
| `bc0cb94` | SQLite `135970191755` (1 failed / 9222 passed / 3 skipped); PG16 `135970191686` | failure / failure |
| `c63d398` local | SQLite: 1 failed / 9222 passed / 3 skipped; **PG16: 1 failed / 9223 passed / 2 skipped** | the only failure in both is the census pin |

The full runs I started on `3f479d9` were stopped (exit 144) because B6.2b replaced that code. They are not
evidence of anything.

## Verification on the final code (`2976b4e` code; `e81b51d` HEAD before this commit)
| Check | Command / source | Result |
|---|---|---|
| Full suite, SQLite (CI) | run `44642957981`, job `135978365627` (`2976b4e`) | **9223 passed, 3 skipped, 0 failed, 0 xfailed** (20 m 22 s) |
| Full suite, PostgreSQL 16 (CI) | run `44642957981`, job `135978365382` (`2976b4e`) | **FAILURE — cause UNEXPLAINED.** Check-run output is empty; the API log tail is service output only; the full-log host is blocked by this environment's proxy. No local reproduction (rows below). **Open: requires a reviewer to read the job log in the GitHub UI.** |
| Full suite, PostgreSQL 16 (CI), same application code | job `135983149197` (`e81b51d`); job `135988689883` (`33a1a47`) | both **success** (counts not retrievable for the reason above). The `2976b4e` failure is therefore intermittent or environmental — **not** shown to be harmless |
| Full suite, SQLite (CI), same code | job `135983149174` (`e81b51d`) success; job `135988690139` (`33a1a47`) **9223 passed, 3 skipped** | — |
| Full suite, SQLite (local, alone) | `cd backend && python -m pytest tests/ -q -rsx` (`e81b51d`) | **9223 passed, 3 skipped, 0 failed, 0 xfailed** (16 m 51 s) |
| Full suite, PostgreSQL 16.15 (local, isolated worktree) | same, fresh PG16 database (`e81b51d`) | **9224 passed, 2 skipped, 0 failed, 0 xfailed** (30 m 12 s) |
| Invalid run (recorded, not evidence) | local SQLite on `e81b51d` **concurrently** with a PG16 run in the same `backend/` directory | 78 failed / 9141 passed / 5 errors. Failures clustered at 0–17 % and 92–96 %; they included `no such column manufacturer_memberships.expires_at` and duplicate rows (`2 == 1`). This is cross-run interference through shared working-directory state; the exact mechanism was not isolated. The same code passed alone (row above) and in CI. Lesson: run suites alone, or in separate worktrees. |
| Skipped | both | `test_benchmarking.py:83` (no hospitals), `test_p10_digital_twin.py:317` (no open alerts); SQLite only: `test_p472_trusted_inference_provenance.py:788` (PG-only Alembic) |
| Expected failures | both | **0 xfailed**. The 15 Batch 5 tripwires were converted by B6.1/B6.2 with assertions unchanged, except GD6-04, which was amended (see review package D′). |
| Sweep, SQLite | `tenant_isolation_matrix.py --sweep sqlite --workdir <fresh>` (`2976b4e`) | **1,913 routes, 0 findings**, 0 foreign-write routes |
| Sweep, PostgreSQL 16.15 | `--sweep postgres --postgres-url …` (`2976b4e`) | 1,913 routes, **0 findings**, 0 foreign-write routes |
| Register / matrix | rebuilt from both sweeps (`e81b51d`) | register empty; two replay routes now tenant-bound (B6.2b); register-driven isolation tests **17/17** |
| Alembic | `alembic heads`; PG16 fresh DB `upgrade head` / guarded `downgrade -1` / `upgrade head` (B6.3) | single head **`b5a2c7e19d40`**; guarded downgrade refuses with an expired membership present; override works |
| Ruff | `ruff check backend/app backend/tests` | All checks passed (CI job `135978365707`) |
| Frontend tests | `npm test` | **48/48** |
| Frontend build | `npm run build` | built (CI job `135978365446`) |
| Browser E2E (Chromium, real login, real backend, no concurrent load) | `frontend/tests/e2e/tenantContext.e2e.mjs` on `e81b51d` | **6/6, twice**. Earlier run at `3f479d9` under load was 5/6 because of a harness race (`c63d398`); there is no app change. Baseline `7cead8a`: 0/6. |
| B6.3 targeted PG16 | tenant context, manufacturer IAM (expiry/revocation), auth role lookup, AW-07, login suites | **76/76** |
| CI security / quality (`2976b4e`) | secret scan ×2, dependency audit, Ruff, frontend build, security baseline, security hardening, compliance, core CI, enterprise quality gate | **all success** |

## Gates
| Gate | Status |
|---|---|
| G1 tenant isolation (resolvers) | technically remediated; **PENDING** non-author review |
| G2 residual register | sweep shows 0 findings; RB-T01 author-converted; **PENDING** review (not closed) |
| G3 AW-07 manufacturer identity | lifecycle partly remediated; grants gated; **OPEN** (GD-9) |
| G4 AW-08 / replay object scope | B6.2b remediated; **PENDING** review |
| G5 GD-3 | **PENDING** review |
| G6 PA-1 | **PENDING** decision |
| G7 GD-5…GD-9, AUTH-1/2, CLIN-1 | **PENDING**: none signed. GD-6 and GD-7 behaviour is blocked (fail closed). |
| G8 clinical workflow | **PENDING** |
| G9 frontend contract | browser 6/6; **PENDING** frontend/API owner review |
| G10 CI security/lint/quality | PASS on `2976b4e` |
| G11 CI backend suites | SQLite and PG16 green on `e81b51d` and `33a1a47`. PG16 on `2976b4e` failed for an **unexplained** cause (**OPEN**). **Not a release pass**: 28 tripwires undispositioned. |
| G12 historical access | **BLOCKED** (needs production access; incident response) |
| G13 independent review | **PENDING**: no reviewer identifiable (1 collaborator, 0 PR reviews) |
| G14 tripwires | **28 release blockers** (0 failing, 28 author-converted), 0 dispositioned |
| G15 release decision | **PENDING** |

**Disposition: PR #181 DRAFT · P472-03 OPEN · HOLD / NO-GO.**
