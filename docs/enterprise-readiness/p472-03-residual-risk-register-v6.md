# P472-03 — Residual Risk Register (v6 — Batch 7)

**PR #181 (DRAFT) · Issue #189** · supersedes v5 (preserved). "Remediated" = an author code fix whose reproduction
now passes. It is **not closed**: closure needs a non-author disposition, and for governance-dependent items a
signed decision. Owners are **roles**. Deadlines are for the release authority to set; none were set by
engineering.

## Security (tenant isolation, authorization)

| ID | Risk | Status after Batch 7 | Residual | Owner (role) | Next step |
|---|---|---|---|---|---|
| R-TRIPWIRE | 33 tripwires: 32 author-converted, 1 failing (RB-T32) | **OPEN — 33 release blockers, 0 dispositioned** | Procedural | release authority (appoint reviewers) | B7.1 packets + ledger |
| R-REVIEWER | No independent reviewer (1 collaborator, 0 PR reviews) | **OPEN** | Procedural — blocks every closure | release authority | appoint per packets §4 |
| **R-GX-WRITE-AUTHZ** | GuardianX source-object writes: tenant B could write evidence/explanations under tenant A's sources (reproduced at `4667ab8`) | **Partly remediated, fail-closed floor (`6a661bb`)** — owned types checked, ownerless-key collisions refused. **NOT independently accepted; NOT fully remediated** | Medium | platform security (GD-7) | non-author review of RB-T29…T31/T33; GD-7 |
| **R-RBT28-COVERAGE** | RB-T28 proves read-side filtering only; it must not be cited as write authorization | **OPEN — documentation/assurance risk** | Procedural | reviewer | review RB-T28 and RB-T29/30 separately |
| **R-GX-EXPLAIN-READ** | Explanations readable cross-tenant (list, replay, audit-evidence package, by id): RB-T32 | **OPEN — failing strict tripwire** | **High** (confidentiality) | platform security (GD-7 scope) | decide explanation ownership; then gate reads |
| R-GX-OWNERLESS-KEYS | Fresh ownerless keys writable by first writer (squatting; no namespace) | OPEN | Low–Medium (availability) | GD-7 | decide key semantics |
| R-GX-WRITE-RACE | Concurrent first writes to a never-used ownerless key both pass (no lock) | OPEN | Low | GD-7 design | namespace keys or add a uniqueness/lock |
| R-GX-LEGACY-CONTAMINATION | Rows injected before Batch 7 remain, verify as valid, and would be classified "attributable" to the injector | OPEN | Unknown (deployed data not examined) | platform security + HIST | migration must check source ownership; HIST |
| R-GX-PKG-TENANTLESS | `/reports/audit-evidence-package` takes no tenant; replay `audit_chain` reports any named resource | OPEN (part of RB-T32 scope) | Medium | platform security | add tenant to the package; owner-scoped chain check |
| R-AW04-feed / R-FEED-DRAFTS | Genesis exposures (RB-T01, RB-T15…T23) | Remediated fail-closed (`38251e6`); review pending | Low | GD-6 owner | packets D′ |
| R-GENESIS-SELF-PUBLISH | Owner-only publish = a tenant can self-publish to the network feed with no second-party control | OPEN — GD-6 | Medium (content integrity / clinical safety) | network/clinical governance | GD-6 |
| R-LEDGER | Ledger cross-tenant reads (RB-T24…T27) | Remediated fail-closed (`3f479d9`); review pending | Low | platform security | packets E′ |
| R-LEDGER-LEGACY | Legacy ledger entries unreadable via tenant APIs | OPEN — operational | Medium (availability) | CLIN-1 / GD-7 | B7.4 packet |
| R-REPLAY-WFX | Replay by id across tenants | Remediated (`00aec32`); review pending | Low | platform security | packet E′ |
| R-SWEEP-BLINDSPOTS | Oracle misses role-gated (164), partly-exercised (727–733), unscoped leads (354), response leakage, IDOR, untyped `payload: dict` bodies (GX-10 was such a case), jobs. Batch 7: the GuardianX write routes now return 422 at the sweep baseline and are only partly exercised; their authorization rests on RB-T29…T33, not on the sweep | **OPEN** | **High** until leads reviewed | security reviewer | B7.1 §3 |
| R-PA1 | Standing platform-admin / dev-token cross-tenant access; log-only | OPEN | **High** | platform security + compliance | PA-1 |
| R-DEVTOKEN-GATING | Dev-token acceptance gated by two env vars (`APP_ENV`/`ENABLE_DEV_AUTH` vs `ENVIRONMENT`); startup check only logs | OPEN | Medium (config-dependent) | platform security | PA-1; unify + refuse at startup |
| R-AW07-PROV | Manufacturer lifecycle; grants gated; pre-Batch-5 rows unprovenanced | Partly remediated | Medium | IAM (GD-9) | GD-9 |
| R-ROLE-ESCALATION-DATA | `users.role` applied on deploy | OPEN — data-dependent | Unknown | authentication + ops (AUTH-2) | inventory before deploy |
| R-HIST | Historical cross-tenant access (incl. GuardianX writes/reads before Batch 6/7) | Not investigated | Unknown | incident response | authorize HIST plan + B7.4 additions |

## Engineering / evidence

| ID | Risk | Status | Owner (role) | Next step |
|---|---|---|---|---|
| **R-CI-PG-INTERMITTENT** | CI PG16 job `135978365382` failed (1 failed / 9223 passed / 2 skipped) | **Root cause identified (author analysis, from the job log): the 00:30 UTC nightly intelligence APScheduler job ran during a route-wide harness case and the process-wide SQL oracle attributed its SQL to the request (route returned 403). Harness guard + 2 regression tests added; deterministic repro 3/5 fail unguarded, 0/7 guarded. Review pending — NOT closed** | engineering + CI owner | reviewer confirms B7.2 report v2 §1–§4 |
| R-SCHED-SHUTDOWN | App lifespan shutdown never calls `_scheduler.shutdown()`; schedulers outlive the lifespan | OPEN | platform owner | B7.2 v2 §6 |
| R-NIGHTLY-SILENT | Nightly intelligence job iterates all tenants and swallows every exception without log/audit | OPEN — observability | platform owner | B7.2 v2 §6 |
| R-ORACLE-SESSION-WIDE | Process-wide SQL oracles can be contaminated by non-scheduler background threads (not inventoried) | OPEN — test-infrastructure | engineering | B7.2 v2 §6 |
| R-CI-PG-EARLIER | PG16 failures on `3f479d9`/`c63d398`/`bc0cb94` | **Confirmed from CI logs: census pin** (was inferred); fixed by the census update | engineering | — |
| R-SUITE-SHARED-STATE | Full suites interfere when run concurrently in one directory (78 failures observed) | OPEN — test-infrastructure | engineering | isolate test DB/file paths per run |
| R-CENSUS-PIN | Census pin forgotten after resolver changes | Process gap (2× now: B6.1, B7) | engineering | reviewer checks census in packets |
| R-E2E-HARNESS | Browser E2E raced under load | Harness fixed; re-run in Batch 7 index | frontend owner | — |
| R-FRONTEND / R-PG-USERS / R-LEDGER-INTEGRITY / R-OIDC-TENANTS | as v5 | unchanged | as v5 | as v5 |

**Release: HOLD / NO-GO.**
