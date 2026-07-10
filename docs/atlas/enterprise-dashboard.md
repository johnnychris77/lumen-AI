# Project Atlas — Enterprise Dashboard & Facility Intelligence

LumenAI v3.1 — Sections 2 & 5

## Endpoints

```
GET /api/atlas/dashboard/{system_id}
GET /api/atlas/facility-intelligence/{system_id}/{facility_id}
```

## Architecture

```
backend/app/services/atlas_dashboard_service.py
frontend/src/components/AtlasDashboard.tsx  — "Enterprise Overview" tab
```

## Facility Intelligence composes existing engines

`compute_facility_intelligence` never re-derives a score that another
service already computes — it composes them:

| Facility Intelligence field | Source |
|---|---|
| `quality_score` | `quality_dashboard_service.executive_quality_score` |
| `risk_score` | `sentinel_dashboard_service.run_sentinel_health_snapshot` |
| `digital_twin_health_pct` | `sentinel_digital_twin_monitor_service.list_open_flags` (100% minus the critical/escalation-tier fraction) |
| `supervisor_agreement_rate` | `sentinel_ai_health_service.compute_ai_health` |
| `training_index` | `competency_service.technician_quality_dashboard` (mean `training_progress_pct`) |
| `knowledge_index` | `knowledge_graph_service.learning_confidence` |
| `health_score` | derived in Atlas itself: mean of `quality_score` and `(100 - risk_score)` |

Every call to `compute_facility_intelligence` persists one
`FacilityIntelligenceSnapshot` row, which Section 7 (analytics/trending)
later buckets by month/quarter/year — the snapshot table exists so trending
never has to recompute historical scores from raw inspection data.

## Enterprise Dashboard is a rollup, not a re-derivation

`enterprise_dashboard(system_id)`:

1. Calls `refresh_all_facility_intelligence`, which recomputes and persists
   a fresh snapshot for every active facility in the system.
2. Averages each numeric field across facilities for the enterprise-level
   score (`enterprise_quality_score`, `enterprise_risk_score`,
   `supervisor_agreement_rate`, `digital_twin_health_pct`,
   `knowledge_growth`).
3. Separately queries `Inspection` rows per facility tenant for
   `inspection_volume`, `pass_rate_pct`, and `coverage_quality_pct` — these
   are enterprise-wide roll-ups of real inspection counts, not scores, so
   they're computed directly rather than through the snapshot.
4. Returns `facility_comparison`, sorted by risk score descending, so the
   highest-risk facility is always first.

## Facility isolation

Every underlying query is scoped by a specific facility's own `tenant_id`
— retrieved from `EnterpriseFacility.tenant_id`, never inferred or
guessed. Two facilities under the same system never share a query;
`atlas_dashboard_service` and `atlas_benchmarking_service` both iterate
facilities one at a time and issue independently-scoped queries per
facility, exactly like `enterprise_dashboards.py`'s existing precedent.

## Response shape

```jsonc
{
  "system_id": "sys-001",
  "facility_count": 3,
  "enterprise_quality_score": 87.4,
  "enterprise_risk_score": 22.0,
  "inspection_volume": 1204,
  "pass_rate_pct": 96.1,
  "coverage_quality_pct": 91.3,
  "ai_confidence_avg": 0.88,
  "supervisor_agreement_rate": 94.2,
  "digital_twin_health_pct": 98.0,
  "knowledge_growth": 0.88,
  "facility_comparison": [ /* one FacilityIntelligenceSnapshot dict per facility */ ],
  "human_review_required": true,
  "disclaimer": "..."
}
```
