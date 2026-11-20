# P472-03 — Security Tripwire Disposition Register (v6 — PA-1 remediation)

**PR #181 (DRAFT) · Issues #190 / #189** · supersedes v5 (preserved). Application code under review `829f36a`
(PA-1 remediation; HEAD adds docs, evidence and the review-kit update only). The rule is unchanged: a failing tripwire is not a passing check, and an
author-converted tripwire is not a closed finding. **Dispositions are recorded only in
`p472-03-batch8-tripwire-disposition-ledger-v3.md`.**

| ID | Test | State on the code under review | Converted by | Assertion | Author notes for the reviewer | Disposition |
|---|---|---|---|---|---|---|
| RB-T01 | `test_no_route_exhibits[AW-04]` (register-driven) | passes; both sweeps 0 findings | `38251e6` | depends on the sweep oracle | oracle blind spots (packets §3) | **PENDING** |
| RB-T02…T08 | findings-file exploit tests | pass | Batch 4 (`5adde8d`, `76d7fc3`, `cea6d7f`) | unchanged (AST-checked by the kit) | exact before-SHAs now per tripwire | **PENDING** |
| RB-T09…T11 | AW-08 tests | pass | `c826fcc` (fixes `fbd2581`, `137e9b1`, `ae54f5e`) | unchanged | before = parent of each fix | **PENDING** |
| RB-T12…T14 | `test_no_route_exhibits[AW-03/06M/06N]` | pass | Batch 4 | register-driven | oracle blind spots | **PENDING** |
| RB-T15…T17, T19…T23 | Genesis GD6-01/02/03/05…09 | pass | `38251e6` | unchanged | fail-closed floor; self-publication open (GD-6) | **PENDING** |
| RB-T18 | Genesis GD6-04 | pass | `38251e6` | **AMENDED** (accepts 403; adds body-absence check) | `after/original` fails by design | **PENDING** |
| RB-T24…T27 | GuardianX GD7-01…04 | pass | `3f479d9` | unchanged | read gate on audit-trail ownership | **PENDING** |
| RB-T28 | GuardianX GD7-05 | pass | `3f479d9` | unchanged; **set-up changed in `6a661bb`** (contaminated state seeded via the service; the HTTP write is now refused) | **READ-SIDE COVERAGE ONLY** — never tested write refusal; must not be read as write authorization | **PENDING** |
| RB-T29 | GD7-06 ledger write under a foreign / missing owned source (3 tests) | pass | `6a661bb` | new; reproduced failing at `4667ab8` (`201 == 404`) | owned types = inspection, workflow_execution only | **PENDING** |
| RB-T30 | GD7-07 ledger write into an ownerless key in use by another owner | pass | `6a661bb` | new; reproduced failing (`201 == 403`) | fresh ownerless keys still writable (GD-7) | **PENDING** |
| RB-T31 | GX-08 explanation under a foreign owned source | pass | `6a661bb` | new; reproduced failing (`201 == 404`) | ownerless explanation writes unchecked (GD-7) | **PENDING** |
| RB-T32 | GX-09 explanations disclosed cross-tenant (list, replay, audit-evidence package, by id) | pass | `c22a879` | **unchanged** (marker removed only); failing strict xfail from `6a661bb` to `83dbf70`, reproduced on SQLite + PG16 | audit-trail ownership floor; chooses no GD-7 option; legacy explanations now unavailable to all (R-GX-EXPLAIN-LEGACY) | **PENDING** |
| RB-T33 | GX-10 `tenant_id_for_digital_twin` names another tenant | pass | `6a661bb` | new; reproduced failing (`201 == 403`) | established AW-04 claim rule | **PENDING** |
| RB-T34 | GX-11 foreign human override by id | pass | `c22a879` | unchanged; committed failing at `eec3bc8` | override is a write; now 404 and nothing persisted | **PENDING** |
| RB-T35 | GX-12 explanation into an ownerless key in use | pass | `c22a879` | unchanged; failing at `eec3bc8` | one key namespace across ledger + explanations | **PENDING** |
| RB-T36 | GX-13 unattributable (legacy) explanation | pass | `c22a879` | unchanged; failing at `eec3bc8` | quarantine, never re-attributed (GD-7/CLIN-1) | **PENDING** |
| RB-T37 | GX-14 replay audit chain without GD-2 scope | pass | `c22a879` | unchanged; failing at `eec3bc8` | GD-2 scope on every replayed chain; mixed chain → 403 | **PENDING** |
| RB-T38 | PA1-01 dev tokens with ENVIRONMENT=production only | pass | `829f36a` | **assertion line unchanged; shared probe helper AMENDED (A-1)**; failing at `6b2a8d6` and `c2014ff` on SQLite + PG16 | configuration now refuses to start; the layer probe shows the dev-token map empty even without `app.main`; kit `after/original` fails by design | **PENDING** |
| RB-T39 | PA1-02 DEMO_MODE public `dev-token` on `/api/demo/reset` in production | pass | `829f36a` | **assertion line unchanged; helper AMENDED (A-1)**; failing at `6b2a8d6` and `c2014ff` (200, seeded row deleted) | refuses to start; demo router alone answers 403 and deletes nothing; public literals still work outside production (R-PA1-NONPROD) | **PENDING** |
| RB-T40 | PA1-03 JWT-shape check ignores APP_ENV / case | pass | `829f36a` | **unchanged** (marker removed only); failing at `6b2a8d6` and `c2014ff` | both configurations still start; check is live at request time | **PENDING** |

Strict xfails failing on the code under review: **0**. Changed assertions and set-up are listed separately in
`p472-03-pa1-remediation-assertion-change-log-v1.md` (A-1…A-4). The full-suite counts are in the release-gate
assessment v8. This is author evidence and does **not** pass the security gate.

**40 release blockers (40 author-converted, 0 failing) · 0 dispositioned · 0 reviewers assigned. HOLD / NO-GO.**
RB-T28 remains **read-side coverage only**. GuardianX write authorization is a fail-closed floor (GD-7 unsigned).
RB-T38…T40 implement a user-directed fail-closed floor; **PA-1 is unsigned** and must ratify or replace it.
