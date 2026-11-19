# ADR — Web Client Tenant Context (P472-03 Batch 5, B5.1)

**Status:** implemented on PR #181 (DRAFT), **pending** frontend-owner and API-owner review (routing #3).
**Issue:** #187 · Closes nothing. Release: **HOLD / NO-GO.**

## Problem (reproduced)
Batch 4 made every client `tenant_id` a *claim* that must equal the caller's verified tenant. The web
client never learned its verified tenant:

* it sent no tenant header, and several screens put a hard-coded or locally stored tenant into requests —
  `AccreditationConsole` (`localStorage.tenant_id || "default-tenant"`, never set), `NetworkIntelligenceConsole`
  (same), `AutonomousOperationsConsole` (`localStorage.tenantId || "demo-tenant"`), `CVInspectionDashboard`
  (`"demo-tenant"`), `VendorIntelligenceDashboard` (`"default-tenant"`), `UpgradeModal` (`"current-tenant"`);
  three of them exposed the tenant as an editable text field;
* no endpoint told the client which tenants the signed-in user may act in, so a multi-membership user had
  no way to select one.

Reproduction on the baseline `7cead8a`:
* API: `TestReproduction` in `backend/tests/test_p472_03_batch5_tenant_context.py` — the console's requests
  for a real tenant → **403**; `GET /api/auth/tenants` → 404 (8 of 23 tests fail before, 23/23 after).
* Browser (Chromium, real login, real backend): console requests `…?tenant_id=default-tenant` → **403**
  on `/readiness` and `/evidence-items`; the page shows "Error: 403 Forbidden". The browser test
  `frontend/tests/e2e/tenantContext.e2e.mjs` fails **0/6** on the baseline frontend and passes **6/6** after.

Also found: two hard-coded credential fallbacks (`Bearer dev-token`) in `RegulatoryComplianceDashboard` and
`DigitalTwinDashboard` (the former also froze the token at module load). Removed.

## Decision
1. **Server is the only source of tenant choices.** New read-only endpoint `GET /api/auth/tenants` returns
   the authenticated caller's **enabled** memberships `[{tenant_id, role}]`, `active_tenant_id` (only when
   exactly one) and `selection_required`. It is derived from the server-side principal
   (`deps.get_current_user` → `tenant_memberships`); headers, query and body cannot add to it; it reveals
   nothing about other users. 401 without a valid token. *(Additive backend contract change — for API-owner
   review.)*
2. **Client selection is advisory.** `TenantProvider` (`frontend/src/lib/tenant.tsx`) fetches the list on
   sign-in, uses the sole tenant, or makes a multi-member user choose (`TenantSwitcher`). The choice is sent
   as `X-Tenant-Id` by the central `apiFetch`; routes that still require a `tenant_id` parameter repeat the
   **same** value (Batch 4 claim rule, GD-5). The server re-verifies membership on every request.
3. **No guessed tenant, ever.** Until the server answers, no tenant header is sent; pages that act in a tenant
   render inside `<RequireTenant>` and make no request without a verified selection. A stored choice
   (`localStorage["lumenai.selectedTenant"]`) is a convenience only: it is discarded unless the server lists
   it again, cleared on logout, and a 403 naming the tenant triggers a re-read.
4. **Platform-wide views are not offered by the UI.** `CommercialConsole`'s free-text tenant / "all tenants"
   health-score filter is removed; the platform-wide view stays a PA-1 privileged API capability whose
   existence is governance decision **GD-8** (unsigned).

## Refusal matrix (tested)
| Case | API test | Browser test |
|---|---|---|
| Single tenant, own data | served (`TestSingleTenantWorkflow`) | served, every request `X-Tenant-Id` = claim = own tenant |
| Multi tenant, explicit selection | served per selection, data kept apart | must choose first; requests follow the choice and the switch |
| Multi tenant, no selection | refused | nothing requested until chosen |
| Forged selection (not a member) | 403 | forged stored value ignored / forces a fresh choice |
| Header ≠ claim; two disagreeing headers | 403 | client never produces either |
| Stale selection (membership revoked) | 403; list no longer contains it | (re-read on tenant 403) |
| No membership | 403; list empty | "not a member of any tenant", nothing requested |
| Another tenant's records | not visible | not visible |

## Not covered / open
* OIDC sessions: `GET /api/auth/tenants` uses the JWT principal (`deps.get_current_user`), the only login the
  web client uses. OIDC principals are not served by it (fail closed: 401).
* `apiFetch(..., { raw: true })` callers do not emit the tenant-denied event (the body is theirs to read).
* Remaining screens send no tenant claim and rely on the header; any future screen must follow this ADR
  (enforced by `frontend/tests/tenantContext.test.mts`, which audits the whole source tree).
* Accessibility/UX review of the switcher has not been done.
