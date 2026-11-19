# P472-03 — Residual Risk Register (v4 — Batch 5)

**PR #181 (DRAFT) · Issue #187** · supersedes v3 (preserved). "Remediated" = code fix in place and its
reproduction passes with the assertion unchanged — **not closed**; closure needs independent review.

| ID | Risk | Status after Batch 5 | Residual severity | Next step |
|---|---|---|---|---|
| R-AW03 / R-AW04 / R-AW06M / R-AW06N / R-RTR / R-AW08 | as v3 | Remediated (Batch 4) — unchanged | Low | Packages A/B |
| R-AW04-feed / R-FEED-DRAFTS | Genesis feed exposures (RB-T01, RB-T15…T23) | **OPEN** — reproduced, unchanged pending GD-6 | Medium | GD-6 |
| R-LEDGER | GuardianX ledger cross-tenant access (RB-T24…T28) | **OPEN** pending GD-7 | Medium | GD-7 |
| R-LEDGER-INTEGRITY | Ledger content/signature edits went undetected | **Remediated** (`3c8d347`); legacy rows now fail verification (unprovable) | Low | Package E review |
| R-AW07-PROV | No manufacturer-membership lifecycle | **Partly remediated** (`de80b7b`): expiry + audited revocation (no route); grants gated closed | Medium (pre-Batch-5 rows have no provenance) | GD-9 |
| R-FRONTEND | Web client sent no tenant header / hard-coded claims (Accreditation 403) | **Remediated** (`189094d`); browser e2e 6/6 (0/6 on baseline) | Low | Routing #3 (frontend owner) |
| R-DEVTOKEN-UI | Two UI components fell back to `Bearer dev-token` | **Remediated** (`189094d`) | Low | Package F |
| R-PG-USERS | `auth_simple` queried non-existent `users.username` | **Remediated** (`e226ee2`); 0 app-issued PG errors | Low | Package F; AUTH-1/AUTH-2 |
| R-ROLE-ESCALATION-DATA | B5.5 now applies `users.role`: a deployed DB with elevated `users.role` values (no assignment row) would grant that role | **OPEN — data-dependent**; no production data examined | Unknown | AUTH-2: inventory before deploy |
| R-TRIPWIRE | 15 failing + 13 converted tripwires | **OPEN — 28 release blockers** | Procedural | Packages A–E |
| R-REVIEWER | No independent reviewer exists in the repository (1 collaborator, 0 reviews) | **OPEN** | Procedural (blocks every closure) | Release authority to appoint reviewers |
| R-PA1 | Platform-admin / dev-token exception | Unchanged | Medium | PA-1 |
| R-LEGACY | NULL-tenant baselines; unattributed data | Quarantined (unchanged) | Low | CLIN-1 |
| R-HIST | Historical cross-tenant access | Not investigated (no production access) | Unknown | Authorized investigation |
| R-OIDC-TENANTS | `/api/auth/tenants` serves JWT principals only; OIDC sessions get 401 there | Known limitation (fail closed) | Low | API owner |

**Release: HOLD / NO-GO.**
