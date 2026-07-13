# LumenAI — Enterprise Operations Center

**Product Evolution Program · Version 1.3: Network · Multi-Site Intelligence, Benchmarking & Enterprise Optimization**

Objectives 1 (Enterprise Operations Center) and 4 (Executive Intelligence) review. A large amount of real, DB-backed aggregation code already exists across Atlas, Sentinel, Pulse, and Vanguard — but most of it is single-tenant despite carrying "enterprise" naming, and the one place genuine multi-facility aggregation exists (Atlas, scoped to one health system's own facilities) has a real, unresolved authorization gap. This document leads with that gap because it is the most consequential finding in this entire Version 1.3 review.

## The most important finding: a real cross-organization authorization gap

**Every Atlas enterprise route (`backend/app/routes/atlas_enterprise.py`) takes `system_id` as a raw URL path parameter and authorizes only on the caller's role (`admin`/`spd_manager`/`operator`/`viewer`) — never on whether that caller actually belongs to the requested `system_id`.** Any authenticated user holding one of those roles can request another health system's enterprise dashboard, benchmarking data, alerts, watchlist, or reports simply by changing the `system_id` value in the URL.

This is not a theoretical concern:
- A real per-user, per-scope table already exists to prevent exactly this (`EnterpriseRoleAssignment`, `atlas_enterprise.py:233-249`, scoped to `system`/`market`/`facility`), with a dedicated service (`atlas_rbac_service.py`) and a `roles/access-check` route — **but none of the actual data-serving endpoints (dashboard, benchmarking, alerts, reports) call it.** The scope-checking mechanism was built and then never wired in.
- The codebase already fixed this exact class of bug once, at the `tenant_id` layer: `backend/app/enterprise_auth.py`'s own comments describe a previously-found gap where a JWT-authenticated user could set `X-Tenant-Id` to a tenant they don't belong to, fixed via `require_enabled_tenant_membership`. **No equivalent membership check exists for `system_id`.**
- The only related test (`test_atlas_enterprise.py::test_dashboard_never_leaks_across_tenants`) verifies that data from two facilities *within the same system_id* doesn't cross-contaminate — a correctness test, not an access-control test. No test asserts that a user scoped to one organization is denied another organization's `system_id`.

**This directly violates this program's own Product Philosophy: "Each organization owns its own data."** Per the user's explicit direction, this review documents the gap in full technical detail rather than fixing it — the fix requires wiring the already-built `atlas_rbac_service` membership check into every Atlas enterprise route, which is a real, scoped, but security-sensitive change that should go through its own reviewed patch, not be bundled silently into a documentation pass. See `docs/product-evolution/v1.3/VERSION_1_3_ROADMAP.md` for this item's priority placement.

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

1. **Close the `system_id` authorization gap before building anything else in this area** — it is the single highest-priority item in this entire Version 1.3 review, and every other enterprise-operations improvement inherits its risk until it's fixed.
2. Retire or rebuild `NetworkDashboardPage.tsx` — it currently presents fabricated demo data as if it were live, with a dead API call underneath.
3. Do not present Sentinel's or Pulse's "enterprise_risk_score"/"enterprise_alerts" as genuinely multi-facility — they are single-tenant; only Atlas's equivalents are real cross-facility rollups.
4. "Regional trends," "improvement opportunities," and "resource utilization" require genuinely new aggregation work — they cannot be assembled from existing, misnamed proxies without misrepresenting what the platform actually computes.
