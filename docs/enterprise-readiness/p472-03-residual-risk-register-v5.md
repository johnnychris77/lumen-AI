# P472-03 — Residual Risk Register (v5 — Batch 6)

**PR #181 (DRAFT) · Issue #188** · supersedes v4 (preserved). "Remediated" = code fix in place, reproduction
passes with the assertion unchanged (or a documented amendment) — **not closed**.

| ID | Risk | Status after Batch 6 | Residual | Next step |
|---|---|---|---|---|
| R-AW04-feed / R-FEED-DRAFTS | Genesis exposures (RB-T01, RB-T15…T23) | **Remediated fail-closed** (`38251e6`); curation authority unresolved | Low (exposure) / Medium (feed is frozen to own-tenant moderation until GD-6) | GD-6; package D′ |
| R-LEDGER | GuardianX cross-tenant reads (RB-T24…T28) + replay embedding (new) | **Remediated fail-closed** (`3f479d9`); no migration | Low (exposure) | GD-7; package E′ |
| R-LEDGER-LEGACY | Legacy ledger entries without provable owner now unreadable via tenant APIs | **New — operational** | Medium (availability of historical evidence) | GD-7 / CLIN-1 |
| R-REPLAY-WFX | Audit replay of workflow executions and rules loaded tenant-owned objects by id with no tenant check | **Remediated** (B6.2b): reproduced 200 → 404; one existing test's set-up corrected (execution now belongs to the replaying tenant; assertions unchanged) | Low | package E′ |
| R-LEDGER-INTEGRITY | Undetected ledger edits | Remediated (`3c8d347`) | Low | package E |
| R-AW07-PROV | Manufacturer lifecycle | Partly remediated (B5.2); grants gated | Medium | GD-9 |
| R-FRONTEND | Accreditation 403 / hard-coded tenants | Remediated (B5.1); browser E2E (see evidence index v5) | Low | routing #3 |
| R-PG-USERS / R-ROLE-ESCALATION-DATA | auth_simple schema; `users.role` now applied | Remediated / OPEN data-dependent | Low / Unknown | AUTH-1/AUTH-2 |
| R-E2E-HARNESS | Browser E2E check raced under load (request from previous tenant counted after the switch) | **Harness fixed** (wait for network idle); no app change. Re-run with no concurrent load on `e81b51d`: 6/6, twice | Low | routing #3 |
| R-CENSUS-PIN | Route-census pin not updated after B6.1, so CI backend jobs on `3f479d9`, `c63d398` and `bc0cb94` failed (1 test) | **Fixed** (`2976b4e`); CI SQLite on `2976b4e` 0 failed | Procedural (process gap: author did not run the census after a resolver change) | reviewer to check census in packages C′/D′ |
| R-CI-PG-INTERMITTENT | CI PG16 job `135978365382` (`2976b4e`) failed. Its cause cannot be read here, and it passed on identical code twice in CI and once locally | **OPEN — unexplained** | Unknown (possible flaky test hiding a real race) | non-author reviewer reads the job log in the GitHub UI |
| R-TRIPWIRE | 28 author-converted tripwires, 0 failing | **OPEN — 28 release blockers** | Procedural | packages A–G |
| R-REVIEWER | No independent reviewer exists | **OPEN** | Procedural | release authority |
| R-PA1 / R-LEGACY / R-HIST / R-OIDC-TENANTS | as v4 | unchanged | as v4 | as v4 |

**Release: HOLD / NO-GO.**
