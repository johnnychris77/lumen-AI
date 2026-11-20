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
| RB-T28 | GuardianX GD7-05 | pass | `3f479d9` | unchanged | **passes via read-side filtering only; foreign write still accepted** | **PENDING** |

Strict xfails failing on the code under review: **0**. Expected-failure count in the full suites: **0 xfailed,
0 xpassed** (see the Batch 7 release-gate index). This is author evidence; it does **not** pass the security gate.

**28 release blockers · 0 dispositioned · 0 reviewers assigned. HOLD / NO-GO.**
