# P472-03 — Batch 4 Remediation Review (v1)

**Issue:** #186 · **PR:** #181 (DRAFT) · **Branch:** `engineering/render-local-inference-p47`
**Baseline:** `4fdac4c` · **Remediation commits:** `5adde8d`, `76d7fc3`, `24ec88d`, `4308443`, `cea6d7f`, `c826fcc`
**Status:** technically remediated, **pending independent review**. Nothing here closes a finding.
Disposition: **PR #181 DRAFT · P472-03 OPEN · release HOLD / NO-GO.**

---

## 1. Baseline (Issue #186 step 1)

Sweep of every mounted route on `4fdac4c` (SQLite), compared with the committed register:

| | Routes | AW-03 | AW-04 | AW-06M | AW-06N |
|---|---|---|---|---|---|
| Register at `4fdac4c` | 186 | 118 | 38 | 122 | 28 |
| Observed by the sweep | 180 | 118 | 32 | 122 | 28 |

The 6-route difference is the batch-3 accreditation routes (claim made inert in `30638f0`), still
registered as a tripwire. **No route outside the register showed a finding.** AW-03 and AW-06M fell on
the same 118 routes in 13 modules (one root cause, §2.1); AW-06M also covered 4 `ranking` routes.

## 2. Remediation groups

Every group: exploit reproduced against the previous commit, fixed, re-run with **assertions unchanged**.

### 2.1 AW-03 / AW-06M — handlers re-read an unverified tenant header (`5adde8d`)
* **Root cause.** 13 modules called `require_enterprise_auth(request)` (which verifies membership),
  discarded the verified context, and re-read the tenant with `get_request_tenant_id(request)`:
  `X-LumenAI-Tenant-Id` was trusted unverified (AW-03); with no header the handler used a shared
  `default-tenant` (AW-06M). A latent auth-layer bug was fixed with it: a multi-member user with no
  header passed a `default-tenant` check and got `tenant_id=None`.
* **Fix.** `tenant_scope.request_tenant(ctx, request)` (tenant of the verified context; a header naming
  another tenant, or disagreeing headers → 403). 138 call sites; `get_request_tenant_id` is no longer
  called by any route module (asserted by a test).
* **Evidence.** Batch-4 tests: 11/19 fail before, 19/19 after. Sweep AW-03 118 → 0, AW-06M 122 → 4.

### 2.2 AW-04 — tenant taken from query / path / body (`76d7fc3`)
* **Rule.** A client `tenant_id` is a **claim**: it must name the verified tenant or be absent; any other
  → 403, never rewritten. Shared check `refuse_other_tenants`; resolvers `request_tenant(…, *claims)`,
  `principal_claim_tenant`, `verified_request_tenant(…, *claims)`.
* **Scope.** 32 swept routes + 7 accreditation **writes** the sweep had not registered (body tenant stored
  verbatim; reproduced by an existing tripwire) + `POST /network-intelligence/lifecycle/events`.
  Batch-3 accreditation reads were tightened from *inert* to *refused*.
* **Also fixed.** `ranking` loaded/wrote findings by id with no tenant predicate (history, PDF, score,
  auto-CAPA) — now 404 for another tenant's finding; schema defaults `"default-tenant"`/`"demo-tenant"`
  now mean "no claim". Infinity partner licences no longer list every tenant's licences on an empty filter.
* **Evidence.** 38 routes × claim-B in every channel: 42 fail before, 0 after. Sweep AW-04 32 → 1,
  AW-06M 4 → 0, foreign-write routes 9 → 0.

### 2.3 `require_tenant_roles` — shared membership dependency, 562 call sites (`24ec88d`, `4308443`)
* **Defects** (found when AW-04 routes using it joined the route-wide harness): disagreeing tenant headers
  accepted (one verified, the other ignored); no header → shared `default-tenant`.
* **Fix.** Either header is the selection (membership asserted); disagreeing → 403; none → sole
  membership; otherwise 403.
* **Latent defect surfaced.** `POST /api/guardianx/evidence` wrote its audit event under `default-tenant`
  (masked while such callers were refused). Now attributed to the verified tenant (`4308443`).

### 2.4 AW-06N — no membership pooled in a literal `default-tenant` (`cea6d7f`)
* 28 routes / 6 modules used `getattr(current_user, "tenant_id", None) or "default-tenant"`; now
  `principal_tenant(current_user, request)`. Analytics keeps its stricter PR #81 rule (non-admin naming a
  tenant needs membership, dev tokens included) — the dev-token exception is not allowed to relax it.
* **Evidence.** 18/18 fail before, 0 after. Sweep AW-06N 28 → 0.

### 2.5 AW-08 — object-level queries (`c826fcc`)
Re-verified the three Day-3 fixes as genuine code fixes (accreditation `fbd2581`, vendor analytics
`137e9b1`, GuardianX replay `ae54f5e`), distinct from the GD-3 whitespace oracle fix (`51c2133`).
Tripwires converted; no strict-xfail marker remains in the findings file.

## 3. Results

| Measure | `4fdac4c` | Final |
|---|---|---|
| Routes with a sweep finding (SQLite) | 180 | **1** |
| Same, PostgreSQL 16 sweep | — | **1** (identical) |
| Register entries | 186 | **1** |
| Modules pinned as remediated (routes) | 189 | **567** |
| Verified-resolver census (dependency / handler) | 195 / 497 | **195 / 714** |
| Strict-xfail tripwires in findings file | 10 (AW-03 1, AW-04 4, AW-06M 1, AW-06N 1, AW-08 3) | **0** |

The remaining route, `GET /api/genesis-ai/manufacturer-updates` (AW-04), is triaged in §5.

## 4. Contract changes (client-visible)
1. A tenant named in **either** header must be one of the caller's enabled memberships; two disagreeing
   headers → 403 (all enterprise, principal and `require_tenant_roles` routes).
2. A member who names no tenant acts in their **sole** membership (was `default-tenant`); a multi-member
   user must select one; a user with no membership → 403.
3. A query/path/body `tenant_id` naming another tenant → 403 (was: served that tenant, or — batch-3
   accreditation — silently ignored). Clients select the tenant with `X-Tenant-Id` and may repeat it.
4. Commercial platform-wide (tenant-less) views: PA-1 privileged class only, logged.
5. **Frontend impact (release-blocking, not fixed here).** The web client sends no tenant header and puts
   hard-coded tenant claims in some requests. `frontend/src/pages/AccreditationConsole.tsx:63` defaults the
   claimed tenant to `localStorage.tenant_id || "default-tenant"`, and nothing in the frontend sets
   `tenant_id` in localStorage. Batch 3 made that accreditation claim inert, so the console worked; Batch 4
   refuses it, so for a user whose tenant is not literally `default-tenant` the console now returns 403
   (fail-closed; no data exposure). Multi-member users are refused on every changed route until the client
   sends `X-Tenant-Id`. Similar hard-coded claims (`DashboardApp.tsx:504` `"demo-tenant"`,
   `VendorIntelligenceDashboard.tsx:184` `"default-tenant"`) target routes that already refused foreign
   claims before Batch 4. Fix options for the API/frontend owner: derive the tenant from the session and
   send it as `X-Tenant-Id`, or stop sending tenant claims (making the backend `tenant_id` query parameters
   optional). Routing #3.
6. Tests updated to the contract: requests now select the tenant they claim (P6, P17, P18, P19, P20,
   ranking, genesis); one genesis test targets the caller's own tenant for "unknown participant → 404" and
   asserts another tenant → 403; one analytics test gives its supervisor a membership.

## 5. Triaged items NOT changed (require review / governance)
| Item | Evidence | Why not changed |
|---|---|---|
| `GET /api/genesis-ai/manufacturer-updates?manufacturer_tenant_id=` (only remaining register entry) | Filters the network knowledge feed by **publisher**; SQL binds the named manufacturer | Publisher filter over network content is plausibly by design; the oracle cannot distinguish it from a caller claim |
| Unpublished manufacturer updates visible to every tenant (list, `/{id}`, version chain) | `list_updates` returns all statuses | Hiding them breaks the review queue until governance decides who curates (GD-6) |
| Any tenant's leadership may publish/reject another manufacturer's update | `review_update` has no ownership check | Curation authority is a governance decision (GD-6) |
| GuardianX evidence ledger has no tenant column | `GET /evidence/{id}`, `?source_type=&source_id=` unscoped | Needs a migration and a decision on whether the ledger is platform-wide (GD-7) |
| Admin-only routes (e.g. p20 sharing agreements, benchmark publish) accept a body `tenant_id` | Platform-administrator operations | PA-1 governance item, unchanged |
| 356 "unscoped SQL" leads in the matrix (81 of the batch-4 ones are the audit hash-chain tail read) | Leads, not findings; e.g. post-insert refresh by PK, network aggregates (GD-1) | Manual review list; none in batch-4 modules was a cross-tenant read |

## 6. Verification
See `p472-03-release-gate-evidence-index-v3.md` for exact commands, counts and CI job ids on the final SHA
(`d62dddc`: SQLite 9111 passed / 3 skipped / 1 xfailed / 0 failed; PostgreSQL 16 9112 / 2 / 1 / 0).

**Tripwires are release blockers, not passes.** The remaining strict xfail (RB-T01) and every tripwire
converted in this batch (RB-T02…T14; §3 "0 markers remain" refers to these author conversions) stay
release blockers until a non-author reviewer records a disposition:
`p472-03-security-tripwire-disposition-v1.md`.
