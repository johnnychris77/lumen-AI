# Project Atlas — Cross-Facility Benchmarking

LumenAI v3.1 — Section 3

## Endpoint

```
GET /api/atlas/benchmarking/{system_id}
```

## Architecture

```
backend/app/services/atlas_benchmarking_service.py
frontend/src/components/AtlasDashboard.tsx  — "Benchmarking" tab
```

## Distinct from `benchmark_engine.py`

`benchmark_engine.py::compute_hospital_benchmarks` groups `CVInferenceRecord`
by a sub-tenant `facility_id` field *within one tenant_id*. Project Atlas
benchmarks across distinct `tenant_id`s (one per hospital) under a health
system, per the tenant==hospital convention established in
`enterprise-model.md`. These are two different axes of comparison and are
not meant to replace one another.

## What's benchmarked

For each facility (90-day lookback, `_LOOKBACK_DAYS`), `compute_facility_
benchmark` returns:

- **Inspection quality** — PASS rate over scored inspections.
- **Coverage** — mean `coverage_pct` across inspections.
- **Finding-type counts** — blood, bone, corrosion, and "damage" (rust,
  corrosion, pitting, crack, insulation damage, missing component — the
  same `_CONDITION_FINDING_TYPES` set Sentinel already uses).
- **Repeat findings** — the same (finding_type, zone) pair recurring ≥3
  times in the window.
- **Supervisor overrides** — count and rate over total inspections.
- **Supervisor reviews** — total review count.
- **Knowledge contributions** — count of `KnowledgeArticle` rows authored
  at that facility (any approval status).
- **Training progress** — mean `training_progress_pct` from `competency_
  service.technician_quality_dashboard`.

`cross_facility_benchmark(system_id)` iterates every active facility under
the system and returns them sorted by inspection quality, descending.

## Data minimization

Every metric returned is a count or a rate. Nothing patient-identifying is
ever aggregated or returned — the same invariant enforced everywhere else
in Atlas (see `enterprise-model.md`).

## Response shape

```jsonc
{
  "system_id": "sys-001",
  "facility_count": 2,
  "facilities": [
    {
      "tenant_id": "hospital-a",
      "facility_id": "fac-001",
      "facility_name": "Mercy General",
      "market_id": "mkt-001",
      "period_days": 90,
      "inspection_quality_pct": 96.4,
      "coverage_pct": 91.0,
      "blood_finding_count": 12,
      "bone_finding_count": 3,
      "corrosion_finding_count": 8,
      "damage_finding_count": 20,
      "repeat_finding_count": 2,
      "total_findings": 44,
      "supervisor_override_count": 5,
      "supervisor_override_rate_pct": 1.2,
      "supervisor_review_count": 60,
      "knowledge_contributions": 4,
      "training_progress_pct": 88.0
    }
  ],
  "human_review_required": true,
  "disclaimer": "..."
}
```
