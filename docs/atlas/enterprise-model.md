# Project Atlas — Enterprise Organization Model

LumenAI v3.1

## Mission

Project Atlas is the cross-facility intelligence layer for multi-hospital
health systems: benchmarking, watchlists, knowledge sharing, analytics,
alerts, executive reporting, and governance across every facility in a
health system — never a re-derivation of the per-facility engines that
already exist, and never an exposure of any facility's patient-identifying
data to another.

## Section 1 is already built

The organization hierarchy (Health System → Market → Region → Facility →
Department) was built in an earlier phase (P16) and needed no new tables or
routes for Atlas:

```
backend/app/models/enterprise_hierarchy.py   — HealthSystem, EnterpriseMarket,
                                                EnterpriseRegion, EnterpriseFacility,
                                                EnterpriseDepartment
backend/app/routes/enterprise_hierarchy.py   — /api/enterprise/systems, /markets,
                                                /regions, /facilities, /departments
```

Atlas only adds the cross-facility intelligence layered on top of this
existing hierarchy.

## What "facility" means

This codebase has, historically, had three incompatible notions of a
sub-tenant "facility": `Inspection.site_name`, `Inspection.facility_name`,
and `CVInferenceRecord.facility_id` — all scoped *within* a single
`tenant_id`. `enterprise_hierarchy.py` took a different, and by now
established, position: `EnterpriseFacility.tenant_id` — a hospital **is** a
distinct `tenant_id`, and a health system spans multiple `tenant_id`s.
`enterprise_dashboards.py::system_quality_dashboard` already relies on this
convention, iterating a system's facilities and querying each one's
`tenant_id` independently.

Project Atlas adopts the same convention throughout. Every Atlas service
resolves "facility" to `EnterpriseFacility.tenant_id`, so:

- Each facility's tenant isolation is preserved exactly as it always has
  been — Atlas reads per-tenant data but never mixes it.
- No new, fourth, incompatible sub-tenant field was introduced.
- "System" = `HealthSystem.system_id`, spanning one or more `tenant_id`s.

## New tables (all additive)

`backend/app/models/atlas_enterprise.py` adds six tables, none of which
replace or duplicate anything:

| Table | Section | Purpose |
|---|---|---|
| `FacilityIntelligenceSnapshot` | 5 | Persisted per-facility score snapshot, reused by Section 7's trending |
| `EnterpriseWatchlistEntry` | 4 | System-scoped watchlist with an explicit risk/improvement `direction` |
| `SharedKnowledgeArticle` | 6 | A publish-a-copy of an approved `KnowledgeArticle`, never a mutation of the source |
| `EnterpriseAlert` | 8 | Explainable, reasoning-backed cross-facility alerts |
| `ExecutiveReport` | 9 | Persisted report metadata + summary JSON, audience-typed |
| `EnterpriseRoleAssignment` | 10 | Scopes a role to a system/market/facility node |

## Data minimization

Every Atlas aggregation reads counts and rates only (inspection counts,
finding-type counts, agreement rates, article counts) — never
patient-identifying data. This holds by construction, consistent with
every other cross-tenant surface in this codebase (`global_intelligence.py`,
`instrument_registry.py`).

## Advisory-only

Every Atlas output — dashboard, benchmark, watchlist entry, alert, and
report — carries `human_review_required: true` and the disclaimer defined
in `app/models/atlas_enterprise.py::DISCLAIMER`. Atlas never claims
causation; findings are framed as "potential association" or "possible
contributing factor," and each facility's own supervisors and local
governance retain full authority over their own operations.
