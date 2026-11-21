# P472-03 — Residual Risk Register (v7 — Batch 8)

**PR #181 (DRAFT) · Issues #190 / #189** · supersedes v6 (preserved). "Remediated" = an author code fix whose reproduction
now passes. It is **not closed**: closure needs a non-author disposition, and for governance-dependent items a
signed decision. Owners are **roles**. Deadlines are for the release authority to set; none were set by
engineering.

## Security (tenant isolation, authorization)

| ID | Risk | Status after Batch 7 | Residual | Owner (role) | Next step |
|---|---|---|---|---|---|
| R-TRIPWIRE | 40 tripwires: 37 author-converted, 3 failing (RB-T38…T40, PA-1) | **OPEN — 40 release blockers, 0 dispositioned** | Procedural | release authority (appoint reviewers) | Batch 8 packets + ledger v2 |
| R-REVIEWER | No independent reviewer (1 collaborator, 0 PR reviews) | **OPEN** | Procedural — blocks every closure | release authority | appoint per packets §4 |
| **R-GX-WRITE-AUTHZ** | GuardianX source-object writes (ledger, explanations, overrides) | **Fail-closed floor** (`6a661bb` + `c22a879`): owned sources must be the caller's; ownerless key = one namespace across ledger + explanations, refused if used by another or an unprovable owner; foreign override 404. **NOT independently accepted; fresh ownerless keys remain first-writer (GD-7)** | Medium | platform security (GD-7) | non-author review of RB-T29…T31, T33…T35 |
| **R-RBT28-COVERAGE** | RB-T28 proves read-side filtering only; it must not be cited as write authorization | **OPEN — documentation/assurance risk** | Procedural | reviewer | review RB-T28 and RB-T29/30 separately |
| **R-GX-EXPLAIN-READ** | Explanations readable cross-tenant (list, replay, package, by id): RB-T32 | **Author-remediated** (`c22a879`): owner = single real tenant on the explanation's audit trail; reproduction now 404/filtered on SQLite + PG16. **Review pending; GD-7 unsigned (interim floor compatible with T and P)** | Medium (until reviewed) | platform security (GD-7) | non-author review of RB-T32, RB-T34…T37 |
| R-GX-OWNERLESS-KEYS | Fresh ownerless keys writable by first writer (squatting; no namespace) | OPEN | Low–Medium (availability) | GD-7 | decide key semantics |
| R-GX-WRITE-RACE | Concurrent first writes to a never-used ownerless key both pass (no lock) | OPEN | Low | GD-7 design | namespace keys or add a uniqueness/lock |
| R-GX-LEGACY-CONTAMINATION | Rows injected before Batch 7 remain, verify as valid, and would be classified "attributable" to the injector | OPEN | Unknown (deployed data not examined) | platform security + HIST | migration must check source ownership; HIST |
| R-GX-PKG-TENANTLESS | `/reports/audit-evidence-package` took no tenant; replay verified any named chain | **Author-remediated** (`c22a879`): package takes the caller's tenant; GD-2 scope on every replayed chain (RB-T37). Review pending | Low | platform security | review RB-T37 |
| R-AW04-feed / R-FEED-DRAFTS | Genesis exposures (RB-T01, RB-T15…T23) | Remediated fail-closed (`38251e6`); review pending | Low | GD-6 owner | packets D′ |
| R-GENESIS-SELF-PUBLISH | Owner-only publish = a tenant can self-publish to the network feed with no second-party control | OPEN — GD-6 | Medium (content integrity / clinical safety) | network/clinical governance | GD-6 |
| R-LEDGER | Ledger cross-tenant reads (RB-T24…T27) | Remediated fail-closed (`3f479d9`); review pending | Low | platform security | packets E′ |
| R-LEDGER-LEGACY | Legacy ledger entries unreadable via tenant APIs | OPEN — operational | Medium (availability) | CLIN-1 / GD-7 | B7.4 packet |
| R-REPLAY-WFX | Replay by id across tenants | Remediated (`00aec32`); review pending | Low | platform security | packet E′ |
| R-SWEEP-BLINDSPOTS | Oracle misses role-gated (164), partly-exercised (727–733), unscoped leads (354), response leakage, IDOR, untyped `payload: dict` bodies (GX-10 was such a case), jobs. Batch 7: the GuardianX write routes now return 422 at the sweep baseline and are only partly exercised; their authorization rests on RB-T29…T33, not on the sweep | **OPEN** | **High** until leads reviewed | security reviewer | B7.1 §3 |
| R-PA1 | Standing platform-admin / dev-token cross-tenant access; log-only | OPEN — PA-1 unsigned; Batch 8 investigation adds PA1-01…07 | **High** | platform security + compliance | PA-1 decision (Batch 8 PA-1 doc §4) |
| R-DEVTOKEN-GATING | Gates read different variables: `deps` (APP_ENV only), startup (APP_ENV or ENVIRONMENT), JWT-shape check (ENVIRONMENT=='production' exact), `validate()` logs only | **OPEN — RB-T38 and RB-T40 failing**; Render config closed (control test) | Medium–High (config-dependent) | platform security | PA-1: single production signal, refuse at startup |
| **R-DEMO-PUBLIC-TOKEN** | `DEMO_MODE=1` serves `/api/demo/*` (incl. the destructive reset of `demo`/`default-tenant` pilot rows) to the public literal `Bearer dev-token`, with no production check | **OPEN — RB-T39 failing**; not set by `render.yaml` | **High if DEMO_MODE is ever set in production** | platform security | PA-1; verify DEMO_MODE in every deployed environment (HIST B2) |
| R-PORTFOLIO-LATENT | `portfolio_authz` role/email grants are dead code (key mismatch); only the literal `dev-token` works. A key "fix" would grant all-tenant, non-anonymised portfolio access to any `tenant_admin` | OPEN — latent | Medium | PA-1 / GD-8 | decide portfolio access before touching the code |
| R-BOOTSTRAP-ADMIN | A personal administrator identity is granted through `render.yaml` (`BOOTSTRAP_TENANT_ADMINS`) with no recorded approval or expiry | OPEN | Medium | PA-1 / AUTH-1 | record approval + expiry or remove |
| **R-GX-EXPLAIN-LEGACY** | Explanations written before Batch 8 have no audit trail and are now served to **no tenant** (availability; count in deployed data unknown) | OPEN — intended quarantine | Medium (availability) | GD-7 + CLIN-1 | release criteria (CLIN-1); HIST snapshot count |
| R-GX-EXPLAIN-SEAL | Explanation content is not sealed into its audit event (unlike the ledger since B5.4); a database writer could edit it undetected | OPEN | Low–Medium | platform security | add content digest under GD-7 |
| R-AW07-PROV | Manufacturer lifecycle; grants gated; pre-Batch-5 rows unprovenanced | Partly remediated | Medium | IAM (GD-9) | GD-9 |
| R-ROLE-ESCALATION-DATA | `users.role` applied on deploy | OPEN — data-dependent | Unknown | authentication + ops (AUTH-2) | inventory before deploy |
| R-HIST | Historical cross-tenant access (incl. GuardianX writes, explanation reads/overrides before `c22a879`, demo/dev-token use) | **Not investigated** — forensic plan + UNSIGNED production-access request in Batch 8 workflows doc | Unknown | incident response | authorize HIST (Part B) |

## Engineering / evidence

| ID | Risk | Status | Owner (role) | Next step |
|---|---|---|---|---|
| **R-CI-PG-INTERMITTENT** | CI PG16 job `135978365382` failed (1 failed / 9223 passed / 2 skipped) | **Root cause identified (author analysis, from the job log): the 00:30 UTC nightly intelligence APScheduler job ran during a route-wide harness case and the process-wide SQL oracle attributed its SQL to the request (route returned 403). Harness guard + 2 regression tests added; deterministic repro 3/5 fail unguarded, 0/7 guarded. Review pending — NOT closed** | engineering + CI owner | reviewer confirms B7.2 report v2 §1–§4 |
| R-SCHED-SHUTDOWN | App lifespan shutdown never calls `_scheduler.shutdown()`; schedulers outlive the lifespan | OPEN | platform owner | B7.2 v2 §6 |
| R-NIGHTLY-SILENT | Nightly intelligence job iterates all tenants and swallows every exception without log/audit | OPEN — observability | platform owner | B7.2 v2 §6 |
| R-ORACLE-SESSION-WIDE | Process-wide SQL oracles can be contaminated by non-scheduler background threads (not inventoried) | OPEN — test-infrastructure | engineering | B7.2 v2 §6 |
| R-CI-PG-EARLIER | PG16 failures on `3f479d9`/`c63d398`/`bc0cb94` | **Confirmed from CI logs: census pin** (was inferred); fixed by the census update | engineering | — |
| R-TESTDB-PERSIST | `backend/test.db` persists between local runs; tests with fixed GuardianX keys (`"42"`, `"77"`, `"500"`) fail on a stale DB now that ownerless keys are first-writer | OPEN — test-infrastructure (CI and fresh worktrees unaffected) | engineering | use unique keys or a fresh DB per run |
| R-SUITE-SHARED-STATE | Full suites interfere when run concurrently in one directory (78 failures observed) | OPEN — test-infrastructure | engineering | isolate test DB/file paths per run |
| R-CENSUS-PIN | Census pin forgotten after resolver changes | Process gap (2× now: B6.1, B7) | engineering | reviewer checks census in packets |
| R-E2E-HARNESS | Browser E2E raced under load | Harness fixed; re-run in Batch 7 index | frontend owner | — |
| R-FRONTEND / R-PG-USERS / R-LEDGER-INTEGRITY / R-OIDC-TENANTS | as v5 | unchanged | as v5 | as v5 |

**Release: HOLD / NO-GO.**
