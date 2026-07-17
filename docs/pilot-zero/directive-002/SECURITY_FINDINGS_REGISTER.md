# LPZ-DIR-002 — Security Findings Register

Each finding below was verified by **direct inspection of the current
branch**, not accepted on report. Evidence cites exact files/lines.
Status vocabulary: CONFIRMED · PARTIALLY CONFIRMED · NOT CONFIRMED ·
REMEDIATED · ACCEPTED RISK · DEFERRED.

---

## F1 — Client-header tenant selection without membership check

* **Severity:** High → **Status: PARTIALLY CONFIRMED / partially REMEDIATED**
* **Affected files:** `app/enterprise_auth.py` (`get_request_tenant_id`
  L59-64, dev/oidc paths), `app/deps.py`, `app/routes/history.py`, ~10
  routes using `getattr(current_user, "tenant_id", None) or
  get_request_tenant_id(request)`.
* **Code evidence:** `get_request_tenant_id` returns
  `x-lumenai-tenant-id | x-tenant-id | "default-tenant"` — a pure header
  read. **However**, the enterprise auth path
  (`_require_dev_auth_context` L162-167, `_require_oidc_auth_context`
  L252-257, `require_enterprise_auth` opens its own db session L314-324)
  **does** verify the header tenant against
  `require_enabled_tenant_membership` before honoring it. So enterprise
  routes fail closed. The gap is the **other** principal
  (`app/deps.get_current_user`), which carried no tenant at all, so the
  ~10 routes above silently fell back to the header.
* **Failure condition:** a route relying on the deps principal + header
  fallback trusts `X-Tenant-Id` outright.
* **Business / Pilot Zero impact:** cross-tenant data exposure; Pilot
  Zero requires strict tenant provenance for every image/record.
* **Remediation (this increment):** the deps principal now carries a
  **membership-verified** `active_tenant_id`, so `getattr(...tenant_id)
  or header` now prefers verified membership; a header can no longer be
  the sole tenant source for any user who has a verified membership. A
  dedicated `resolve_verified_tenant` rejects a requested tenant that is
  not in verified memberships (403).
* **Test:** `test_directive_002_tenant_context.py::TestResolveVerifiedTenant`
  (unverified requested tenant → 403).
* **Disposition:** header-fallback routes remain in
  `TENANT_MIGRATION_INVENTORY.md` for explicit per-route migration to
  `resolve_verified_tenant` (DEFERRED to increment 2+).

## F2 — Authenticated principal lacked tenant/identity fields

* **Severity:** High → **Status: CONFIRMED / REMEDIATED (contract) **
* **Affected files:** `app/deps.py` L83-101 (pre-change).
* **Code evidence (pre-change):** `get_current_user` returned
  `SimpleNamespace(id=0, email=..., role=...)` — no `tenant_id`, no
  memberships, no active tenant, `id=0` for **every** JWT user.
* **Failure condition:** any code reading `current_user.tenant_id` got
  `None`; identity could not be tied to a user or tenant.
* **Impact:** the direct cause of F3 (fail-open) and of unattributable
  actions.
* **Remediation:** typed `AuthenticatedPrincipal`
  (`app/security/principal.py`) — subject, email, username, role,
  verified `tenant_memberships`, `active_tenant_id`,
  `authentication_method`, token id/iat/exp; both dev and JWT paths
  implement it; backward-compatible `.id`/`.tenant_id` aliases.
* **Test:** `TestAuthenticatedPrincipalContract`.
* **Disposition:** REMEDIATED for the contract; `user_id` remains 0
  until user rows carry a stable id resolvable from `sub` (DEFERRED,
  noted in `AUTHENTICATED_PRINCIPAL_SPECIFICATION.md`).

## F3 — Tenant-scoped query fails OPEN when tenant_id is missing

* **Severity:** **Critical** → **Status: CONFIRMED / REMEDIATED**
* **Affected files/endpoints:** `app/routes/history.py` — `/history`,
  `/history/summary`, `/history/export.json|.csv|.xlsx|.bundle.zip`.
* **Code evidence (pre-change):** `_tenant_id_for_user` returned
  `getattr(current_user, "tenant_id", None)` (always `None`, per F2) for
  non-admins; `fetch_rows(db, tenant_id=None)` did `if tenant_id:` →
  **filter skipped → all tenants returned.**
* **Exploit:** any authenticated `spd_manager` / `vendor_user` /
  `viewer` of any tenant calls `/api/history` (or an export) and
  receives **every tenant's** inspection records — a cross-tenant data
  breach, reproducible with a single GET.
* **Impact:** confidentiality breach across hospitals; disqualifying for
  Pilot Zero data governance.
* **Remediation:** `fetch_rows(*, all_tenants, tenant_id)` requires an
  explicit `all_tenants` flag; only a verified platform admin gets it;
  every other principal is confined to a membership-verified tenant, and
  a missing verified tenant raises **403** (never unfiltered).
  Route uses `resolve_verified_tenant`.
* **Test:** `TestHistoryCrossTenantIsolation::test_non_admin_without_membership_is_denied_not_unfiltered`
  and `..._export_...` (403, not all-tenants);
  `test_admin_sees_all_tenants` (explicit admin).

## F4 — Write endpoints lacking auth/authorization

* **Severity:** High → **Status: DEFERRED (inventory in progress)**
* **Evidence:** enumerating all mounted routes and their dependencies is
  under way in `ENDPOINT_INVENTORY.md`; unauthenticated **write**
  endpoints are the prioritized subclass. No unauthenticated writer has
  been *confirmed* yet in this increment; the history increment did not
  touch writers. This finding is **not closed** — closing it requires
  the completed endpoint inventory (next increment).
* **Disposition:** DEFERRED with a concrete deliverable
  (`ENDPOINT_INVENTORY.md`, all endpoints classified; zero UNCLASSIFIED
  before Directive 002 closes).

## F5 — Multiple overlapping authentication implementations

* **Severity:** Medium → **Status: CONFIRMED / DOCUMENTED**
* **Evidence:** `app/deps.py::get_current_user` (dev-token + app JWT),
  `app/enterprise_auth.py` (dev / OIDC contexts + membership check +
  app-JWT fallback), `app/auth/__init__.py`, `app/routers/auth.py`,
  `app/routers/auth_simple.py` (issuer/`_user_role`). Two are
  load-bearing: **deps.get_current_user** (role-gated interactive
  routes via `authz.require_roles`) and **enterprise_auth.get_auth_context**
  (tenant-scoped enterprise routes). They now share the typed principal's
  intent (membership-verified tenant) but remain separate code paths.
* **Disposition:** consolidation is architecturally significant and is
  **not** done in one PR (execution rule 3). Documented in
  `AUTHENTICATED_PRINCIPAL_SPECIFICATION.md` §Migration; DEFERRED.

## F6 — Audit events recording `unknown` / dev actor

* **Severity:** Medium → **Status: CONFIRMED / PARTIALLY REMEDIATED**
* **Evidence:** `app/enterprise_auth.get_request_actor` L46-52 falls
  back to `"unknown"` from headers; audit writer accepts `actor="system"`
  default. The typed principal now provides a verified `email`/`subject`
  and `authentication_method` that audit calls can attribute from.
* **Disposition:** the actor-attribution contract is specified in
  `AUDIT_ACTOR_SPECIFICATION.md`; wiring every audit call to read the
  principal (rather than a header) is DEFERRED to increment 2. Current
  increment does not regress attribution.

## F7 — Duplicate / conflicting / unreproducible dependency manifests

* **Severity:** Medium → **Status: CONFIRMED / REMEDIATED (WS1)**
* **Evidence:** already fixed under Pilot Zero WS1 (merged): root
  `requirements.txt` was stale/divergent, `backend/requirements.txt`
  listed `psycopg2-binary` three times. Now: `backend/requirements-lock.txt`
  (tested pins), root `requirements.txt` generated from it,
  `backend/requirements.txt` deduplicated. `pip-audit` + `npm audit`
  clean. See `BUILD_REPRODUCIBILITY_REPORT.md`.

## F8 — Placeholder scorer indistinguishable from validated model

* **Severity:** High → **Status: CONFIRMED / structurally REMEDIATED (contract)**
* **Evidence:** `app/services/baseline_comparison_scoring_service.py`
  produces deterministic scores; results did not carry a machine-readable
  capability envelope declaring them non-validated / GT-ineligible.
* **Remediation (this increment):** `app/security/engine_capability.py`
  defines the maturity ladder (PLACEHOLDER → PRODUCTION_MODEL) and a
  fixed `placeholder_capability()` (engine_type=PLACEHOLDER,
  validation_status=NOT_VALIDATED, clinical_use_permitted/ground_truth_
  eligible/performance_reporting_eligible=False, human_review_required=
  True), plus `assert_not_placeholder_for_ground_truth` guard.
* **Test:** `test_directive_002_placeholder_isolation.py` (placeholder
  cannot enter Ground Truth or performance reporting).
* **Disposition:** stamping every scoring result with the capability
  block, and enforcing the guard inside the GT-approval and
  performance-reporting code paths, is DEFERRED to increment 2
  (`PLACEHOLDER_ISOLATION_POLICY.md`).
