# P472-03 — Release Gate Evidence Index (v3 — Batch 4)

**PR #181 (DRAFT)** · **Issue #186** · supersedes `p472-03-release-gate-evidence-index-v2.md` (preserved).
Legend: **PASS** (evidence recorded) · **PENDING** (awaiting a run or an independent human action) ·
**BLOCKED** · **FAIL / OPEN**. A technical PASS is not an independent review. **Overall gate: NO-GO.**

## Verification evidence (Batch 4)
| Check | Code | Command / source | Result |
|---|---|---|---|
| Full suite, SQLite (local) | `c826fcc` | `cd backend && DATABASE_URL=sqlite:///./full_final.db python -m pytest tests/ -q` | **9111 passed, 3 skipped, 1 xfailed, 0 failed** (17 m 19 s). The xfail is `test_no_route_exhibits[AW-04]` — the strict guard for the one open route. |
| Full suite, SQLite (CI) | `7605885` | run `44601411830`, job `135833512225` | **PENDING** (running at time of writing) |
| Full suite, PostgreSQL 16 (CI) | `7605885` | run `44601411830`, job `135833512159` | **PENDING** (running at time of writing) |
| Earlier CI, SQLite | `4308443` | job `135820641506` | 3 failed (the AW-08 tripwires, converted in `c826fcc`) / 9012 passed / 3 skipped / 3 xfailed |
| Application-wide sweep, SQLite | `c826fcc` | `scripts/tenant_isolation_matrix.py --sweep sqlite` | 1,912 routes; **1** with a finding (`GET /api/genesis-ai/manufacturer-updates`, AW-04) |
| Application-wide sweep, PostgreSQL 16.15 | `c826fcc` | `--sweep postgres` (scratch schemas) | 1,912 routes; **1** with a finding — identical to SQLite |
| Findings register | `7605885` | rebuilt from both sweeps (`--write-register --also`) | 1 entry; `unstable: {}`; sweeps `[sqlite, postgresql]` |
| Alembic chain, PostgreSQL 16 | `c826fcc` | fresh DB: `alembic heads`; `upgrade head`; `downgrade -1`; `upgrade head` | single head `e7c2a9f04b18`; all steps succeeded |
| Ruff | `c826fcc` | `ruff check backend/app backend/tests` | All checks passed |
| Frontend build | `c826fcc` | `npm --prefix frontend run build` | built |
| CI security & quality gates | `7605885` | run `44601411830` + sibling runs | secret scan ×2, ruff, frontend build ×2, compliance, security-and-lint, security hardening, dependency audit, core CI, enterprise quality gate: **11/11 success** |

## Gates
| Gate | Criterion | Status |
|---|---|---|
| G1 | Tenant isolation — verified resolvers (Batches 1–4) | Technically PASS (sweep: 1 route); **PENDING** independent review |
| G2 | Residual register (was 186 routes) | **FAIL / OPEN** — 1 route (GD-6) |
| G3 | AW-07 manufacturer identity | Authorization PASS; **OPEN** provisioning/revocation workflow + IAM review |
| G4 | AW-08 object-level | Technically PASS (re-verified); **PENDING** review |
| G5 | GD-3 floor + migration | **PENDING** review |
| G6 | PA-1 platform-admin / dev-token exception | **PENDING** governance decision |
| G7 | GD-1 … GD-8 | **PENDING** (none signed) |
| G8 | Clinical workflow / legacy attribution | **PENDING** clinical owner |
| G9 | Frontend contract impact (R-FRONTEND: AccreditationConsole refused for real tenants; no tenant header sent) | **FAIL / OPEN** — release-blocking |
| G10 | CI security / lint / compliance / quality | PASS on `7605885` (11/11) |
| G11 | CI backend suites (SQLite, PostgreSQL 16) on the final SHA | **PENDING** (running) |
| G12 | Historical access investigation | **BLOCKED** (needs authorization; no production access) |
| G13 | Independent human security review | **PENDING** — every routing slot UNASSIGNED |
| G14 | Authorized release decision | **PENDING** — not recorded |

## Determination
G2 and G9 are open; G11 is pending; no independent review or release decision is recorded.
**Disposition: PR #181 DRAFT · P472-03 OPEN · release HOLD / NO-GO.**
