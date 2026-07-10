# Project Vanguard — Financial & Operational Intelligence

LumenAI OS v4.6 — Sections 3, 4, 8

## Financial Intelligence (Section 3)

Financial signal in this codebase was fragmented across three places
before this sprint — checked in full first:

* `prediction_engine.compute_predictive_dashboard` — already computes
  real `projected_repair_cost_usd`/`projected_replacement_cost_usd`/
  `repair_avoidance_roi_usd` from `estimated_repair_cost_usd`/
  `estimated_replacement_cost_usd` fields on real `RepairForecast` rows
  (falls back to seeded mock data only when no real rows exist yet —
  `data_source` is always surfaced verbatim, never hidden).
* `executive.py`'s `cfo` KPI branch — a marketing-style ROI formula with
  hard-coded constants, not genuine per-unit cost data (see
  `executive-intelligence.md`'s naming-disambiguation note). Not reused.
* `or_connect.py`'s `RepairRequest` — confirmed no cost field exists at
  the case-coordination layer at all.

`vanguard_financial_service.financial_intelligence` composes
`prediction_engine.compute_predictive_dashboard` (repair cost trend,
avoided replacement cost, capital replacement priorities),
`digital_twin_engine`'s real `utilization_pct` (instrument utilization),
and `or_connect_service.clinical_engineering_summary`'s real repair
turnaround (the closest existing reprocessing-efficiency signal).

**"Inspection cost trends" is the one line item this codebase has no
real per-inspection labor/reagent cost data for anywhere** (confirmed:
no cost field on `Inspection`, none on `RepairRequest`). Rather than
invent a dollar figure, this reports the real inspection-volume trend
as an explicit, labeled operational proxy — consistent with this
codebase's established convention of reporting `not_applicable`/an
honest proxy rather than fabricating a number Pulse's AI Ops Monitor
already set for GPU/CPU utilization.

```
GET /api/vanguard/financial
```

## Operational Intelligence (Section 4)

Composes `or_connect_service.executive_dashboard` (OR delays, repair
backlog, inspection turnaround, bottlenecks), `pulse_kpi_service.
live_kpis` (inspection quality, throughput, instrument availability),
and `competency_service.technician_quality_dashboard` (staffing) — none
of their arithmetic is recomputed here.

"Correlate" is implemented as a **real Pearson correlation coefficient**
between two aligned weekly time series — open-repair count and
delayed-case-readiness-score count — not a fabricated relationship, and
explicitly labeled: a correlation is not causation, and
`human_review_required` applies here exactly as it does everywhere else
in this codebase.

```
GET /api/vanguard/operational
```

## Enterprise Benchmarking (Section 8)

`atlas_benchmarking_service.cross_facility_benchmark`/
`compute_facility_benchmark` already compute a real per-facility rollup
(inspection quality, coverage, findings, supervisor overrides, knowledge
contributions, training progress) across every facility in a system.
All six named benchmark dimensions re-slice that same real data (or add
one real per-facility signal, e.g. Digital Twin utilization for
"instrument health") rather than re-querying `Inspection`/
`SupervisorReview` a second time:

| Dimension | Source |
|---|---|
| Facilities | `atlas_benchmarking_service.cross_facility_benchmark` directly |
| Markets | Same facility list, grouped by `EnterpriseFacility.market_id` |
| Service Lines | Real `SurgicalCase.service_line` volume + `CaseReadinessScoreRecord` averages |
| Inspection Programs | Same facility list, re-sorted by `inspection_quality_pct` |
| Instrument Health | Digital Twin utilization per facility |
| Knowledge Maturity | Same facility list's `knowledge_contributions`/`training_progress_pct` |

```
GET /api/vanguard/benchmarking/{benchmark_type}
```
