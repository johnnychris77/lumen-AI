# LumenAI — Enterprise Operations Center

**Product Evolution Program · Version 1.3: Network · Multi-Site Intelligence, Benchmarking & Enterprise Optimization**

Objectives 1 (Enterprise Operations Center) and 4 (Executive Intelligence) review. A large amount of real, DB-backed aggregation code already exists across Atlas, Sentinel, Pulse, and Vanguard — but most of it is single-tenant despite carrying "enterprise" naming, and the one place genuine multi-facility aggregation exists (Atlas, scoped to one health system's own facilities) had a real cross-organization authorization gap. **That gap has now been fixed and wired in** — this document keeps the finding in full because it is the most consequential one in this entire Version 1.3 review, and the fix's details matter for anyone extending these routes.

## Fixed: the cross-organization authorization gap

**Previously, every Atlas enterprise route (`backend/app/routes/atlas_enterprise.py`) took `system_id` (and sometimes `facility_id`) as a raw URL path parameter and authorized only on the caller's role (`admin`/`spd_manager`/`operator`/`viewer`) — never on whether that caller actually belonged to the requested `system_id`.** Any authenticated user holding one of those roles could request another health system's enterprise dashboard, benchmarking data, alerts, watchlist, or reports simply by changing the `system_id` value in the URL.

This was not a theoretical concern:
- A real per-user, per-scope table already existed to prevent exactly this (`EnterpriseRoleAssignment`, `atlas_enterprise.py:233-249`, scoped to `system`/`market`/`facility`), with a dedicated service (`atlas_rbac_service.py`) — **but none of the actual data-serving endpoints (dashboard, benchmarking, alerts, reports) called it.** The scope-checking mechanism had been built and then never wired in.
- The codebase had already fixed this exact class of bug once, at the `tenant_id` layer: `backend/app/enterprise_auth.py`'s own comments describe a previously-found gap where a JWT-authenticated user could set `X-Tenant-Id` to a tenant they don't belong to, fixed via `require_enabled_tenant_membership`. This fix applies the same pattern at the `system_id`/`facility_id` layer.

**The fix**: every Section 2-9 data-serving route (dashboard, benchmarking, watchlists, facility intelligence, knowledge sharing, analytics, alerts, executive reports) now runs a `_require_scope()` dependency after the existing role check — it reads `system_id`/`facility_id` from the request path and calls `atlas_rbac_service.user_has_scope_access()`, rejecting with `403` if the caller holds no `EnterpriseRoleAssignment` covering that organization (or an ancestor of it — a system-level grant implies access to every market/facility beneath it). `POST /knowledge/share` gets the same check inline, since its `system_id` arrives in the JSON body rather than the URL path. The one route where the scope_id can't always resolve (`facility-intelligence`, when `facility_id` doesn't exist) falls back to checking the `system_id` already present in that same route's path, so an unknown facility still correctly reaches the route's own `404`, rather than masking it behind an opaque `403`.

**Escalation prevention**: `POST /roles/grant` (Section 10) now also requires the granter to already hold scope access to the `scope_id` they're granting into — with a single, deliberate exception: `admin` may grant a role into a system with no pre-existing assignments, since that's the only way to bootstrap a brand-new organization's first role. Every other leadership role must already hold real scope access before it can grant further roles within it, closing the self-grant bypass that would otherwise let a leadership user from one organization grant themselves access to another.

**Test coverage**: `test_atlas_enterprise.py::TestSystemAccessEnforcement` adds explicit proof — a fresh system with no grants returns `403`, granting access via `POST /roles/grant` then makes the same request succeed, a system-level grant is proven to cover a facility beneath it, and a leadership user is proven unable to grant into a system it doesn't itself have access to. `_setup_system()` (used by the rest of the file's ~25 existing tests) now pre-grants the dev-auth identities (`admin@local.dev`/`spd_manager@local.dev`/`viewer@local.dev`) system-level access to each freshly-created test system, mirroring realistic onboarding, so those tests continue to exercise business logic rather than the access gate itself.

**This closes the gap against this program's own Product Philosophy: "Each organization owns its own data."** See `docs/product-evolution/v1.3/VERSION_1_3_ROADMAP.md` for this item's (now-complete) Stage 0 status.

## Enterprise Operations Center — field-by-field reality

| Required field | Status | Basis |
|---|---|---|
| Operational Health | Exists, wrong module, single-tenant | `maestro_health_index_service.compute_operational_health()` — real but tenant-scoped, lives in Maestro not Vanguard/Atlas |
| Risk Summary | Exists, mostly single-tenant | Sentinel's `_compute_enterprise_risk_score` is per-`tenant_id` despite its name; Atlas genuinely averages facility risk scores system-wide (`atlas_dashboard_service.py`'s `_avg("risk_score")`) |
| Inspection Throughput | Real, multi-facility in Atlas | `atlas_dashboard_service.py` sums `inspection_volume` across every facility in a system |
| Facility Status | Real data exists (Atlas); the frontend page named for this is fake | `atlas_dashboard_service.py`'s `facility_comparison` is real; **`NetworkDashboardPage.tsx` hardcodes `DEMO_FACILITIES` and calls `/api/enterprise/network-snapshot`, an endpoint that does not exist anywhere in the backend** — the fetch always fails and silently falls back to mock data |
| Digital Twin Health | Real, multi-facility in Atlas | `atlas_dashboard_service.py` computes and averages `digital_twin_health_pct` across facilities; note `digital_quality_twin_service.py`'s twin score is separately flagged in-repo as "a seeded-mock placeholder pending real multi-source wiring" — do not conflate the two |
| Quality Indicators | Real, multi-facility in Atlas | `enterprise_quality_score` — a genuine average of per-facility `quality_score` |
| Enterprise Alerts | Real cross-facility rollup exists only in Atlas | Pulse's and Sentinel's "enterprise_alerts" are both actually single-tenant despite the name; Atlas's dedicated `EnterpriseAlert` model + `atlas_alert_service.generate_enterprise_alerts(db, system_id)` is the one genuine multi-facility alert aggregator |

**Net finding**: a genuine Enterprise Operations Center is buildable almost entirely from Atlas's existing, real, system_id-scoped aggregation — but it must first close the authorization gap above, and it should not be built from Sentinel's or Pulse's "enterprise"-named-but-actually-single-tenant equivalents.

## Executive Intelligence (Vanguard) — field-by-field reality

`vanguard_executive_intelligence_service.executive_intelligence_center()` composes 8 dimensions from existing services (explicitly documented as recomputing nothing fresh). Against this objective's 7 required fields:

| Required field | Status |
|---|---|
| Executive scorecards | **Real** — `vanguard_scorecard_service.py`, 8 audience-specific scorecards (CEO/COO/CNO/CMO/VP Surgical/Quality/Supply Chain/SPD Director), persisted via `ExecutiveScorecardSnapshot` |
| Regional trends | **Missing** — no field or service literally named this exists anywhere in the backend; the closest analog groups by `market_id`, not region |
| Capacity analysis | **Exists, but thin** — `vanguard_executive_intelligence_service.py`'s own docstring admits: "No dedicated 'facility capacity' model exists anywhere in this codebase; this is the closest real, non-fabricated proxy" (digital-twin utilization + today's OR case count) |
| Quality summaries | **Real** — Atlas's system-wide quality score (when resolvable) plus `vanguard_operational_service.py`'s `inspection_quality` |
| Risk summaries | **Real, but single-tenant** — sourced from Pulse→Sentinel's tenant-scoped risk score, not a genuine multi-organization risk view |
| Improvement opportunities | **Missing** — no field/service by this name exists anywhere; Apollo's `apollo_improvement_portfolio_service.py` is conceptually related but department-scoped and not wired into Vanguard at all |
| Resource utilization | **Missing** — only the same thin capacity proxy (instrument/twin utilization), not staffing or broader resource utilization |

## Recommendation

1. ~~Close the `system_id` authorization gap before building anything else in this area~~ — **done**; every Atlas enterprise route now enforces real organizational scope, not just role.
2. Retire or rebuild `NetworkDashboardPage.tsx` — it currently presents fabricated demo data as if it were live, with a dead API call underneath.
3. Do not present Sentinel's or Pulse's "enterprise_risk_score"/"enterprise_alerts" as genuinely multi-facility — they are single-tenant; only Atlas's equivalents are real cross-facility rollups.
4. "Regional trends," "improvement opportunities," and "resource utilization" require genuinely new aggregation work — they cannot be assembled from existing, misnamed proxies without misrepresenting what the platform actually computes.
