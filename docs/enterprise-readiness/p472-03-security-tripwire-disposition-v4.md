# P472-03 — Security Tripwire Disposition Register (v4 — Batch 7)

**PR #181 (DRAFT) · Issue #189** · supersedes v3 (preserved). Code under review `2976b4e` (unchanged at the
Batch 7 head). Rule unchanged: a failing tripwire is not a passing check; an author-converted tripwire is not a
closed finding. **Dispositions are recorded only in `p472-03-batch7-tripwire-disposition-ledger-v1.md`.**

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
| RB-T32 | GX-09 explanations disclosed cross-tenant (list, replay, audit-evidence package, by id) | **FAILS — strict xfail (OPEN)** | — | new; reproduced | no owner column, no audit trail; pending GD-7 | **OPEN — not converted** |
| RB-T33 | GX-10 `tenant_id_for_digital_twin` names another tenant | pass | `6a661bb` | new; reproduced failing (`201 == 403`) | established AW-04 claim rule | **PENDING** |

Strict xfails failing on the code under review: **1** (RB-T32) as of `6a661bb`; **0** on `2976b4e`. Expected-failure count in the full suites: **0 xfailed,
0 xpassed** (see the Batch 7 release-gate index). This is author evidence; it does **not** pass the security gate.

**33 release blockers (32 author-converted + 1 failing) · 0 dispositioned · 0 reviewers assigned. HOLD / NO-GO.**
GuardianX write authorization is **not remediated**: RB-T29…T31/T33 are a fail-closed floor for what existing
policy settles; ownerless-key semantics and explanation ownership remain open (GD-7). See
`p472-03-batch7-gd7-05-write-side-authorization-v1.md`.
