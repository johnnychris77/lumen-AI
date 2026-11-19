# P472-03 — Residual Risk Register (v3 — Batch 4)

**PR #181 (DRAFT)** · **Issue #186** · supersedes `p472-03-residual-risk-register-v2.md` (preserved).
Residual severity is the exposure given the code at the final Batch 4 SHA. "Remediated" means the code fix
is in place and its reproduction test passes with the assertion unchanged — **not closed**; closure needs
the independent review in `p472-03-independent-review-routing-v2.md`.

| ID | Risk | Status after Batch 4 | Residual severity | Next step |
|---|---|---|---|---|
| R-AW03 | Foreign `X-LumenAI-Tenant-Id` binds data | **Remediated** (`5adde8d`); 0 routes in SQLite and PG16 sweeps | Low | Independent review (routing #2) |
| R-AW04 | Foreign tenant in query/path/body | **Remediated** (`76d7fc3`) except one publisher-filter route | Low | Review #2; GD-6 for the remaining route |
| R-AW04-feed | `GET /api/genesis-ai/manufacturer-updates?manufacturer_tenant_id=` | **OPEN** (only register entry); publisher filter over network content | Low–Medium (depends on GD-6) | GD-6 decision |
| R-AW06M | Members pooled in `default-tenant` | **Remediated** (`5adde8d`, `76d7fc3`, `24ec88d`) | Low | Review #2 |
| R-AW06N | No-membership users pooled in `default-tenant` | **Remediated** (`cea6d7f`) | Low | Review #2 |
| R-RTR | `require_tenant_roles` split headers / default fallback (562 call sites) | **Remediated** (`24ec88d`) | Low | Review #2 |
| R-AW08 | Unscoped object-level reads (accreditation, vendor analytics, replay, ranking) | **Remediated** (Day 3; ranking in `76d7fc3`); tripwires converted | Low | Review #4 |
| R-FEED-DRAFTS | Unpublished manufacturer updates visible to every tenant; any tenant leadership may publish/reject | **OPEN** — governance-dependent | Medium (pre-release content disclosure; integrity of the feed) | GD-6 |
| R-LEDGER | GuardianX evidence ledger rows not tenant-scoped | **OPEN** — governance-dependent | Medium (if ledger is tenant-owned) | GD-7 |
| R-AW07-PROV | No provisioning/revocation workflow or audit for manufacturer memberships | **OPEN** | Medium (unaudited grants; fail-closed until provisioned) | IAM review (routing #6) |
| R-PA1 | Platform-admin / dev-token cross-tenant exception | Unchanged, logged (not tamper-evident) | Medium | Platform-security decision (routing #7) |
| R-CONTRACT | Batch 4 refuses requests that used to be served (foreign claims, no-membership users, multi-member without selection) | Intended; clients that relied on the old behaviour will see 403 | Operational | API/frontend owner review (routing #3) |
| R-FRONTEND | Web client sends no tenant header and hard-coded tenant claims; AccreditationConsole claims `"default-tenant"` (`AccreditationConsole.tsx:63`) and is now refused for real tenants | **OPEN — release-blocking functional regression** (fail-closed, no exposure) | High (availability of accreditation console; multi-member users blocked on changed routes) | Frontend change: send the session tenant as `X-Tenant-Id` or stop sending claims (routing #3) |
| R-LEGACY | NULL-tenant vendor baselines + unattributed data | Quarantined fail-closed (unchanged) | Low | Clinical attribution packet |
| R-HIST | Whether any cross-tenant access occurred historically | Not investigated (no production access) | Unknown | Authorized investigation per `p472-03-historical-access-investigation-plan.md` |

## Aggregate
The application-wide sweep (SQLite and PostgreSQL 16) shows one route with a finding, down from 180.
The remaining risks are governance-dependent (GD-6, GD-7, PA-1), identity-lifecycle (AW-07 provisioning),
historical (unknown) and procedural (no independent review yet). **Release: HOLD / NO-GO.**
