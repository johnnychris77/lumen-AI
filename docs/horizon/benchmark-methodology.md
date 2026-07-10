# Project Horizon — Benchmark Methodology

LumenAI v3.4 — Sections 4 & 5

## Reusing P15's exact percentile-band + Laplace-noise pattern

`horizon_benchmark_service.py` imports `MIN_FACILITIES` and
`_add_laplace_noise` directly from `network_benchmark_service.py` (P15) —
the same math, applied to six new metric names P15 doesn't compute.
Section 5 explicitly asks to "display percentiles rather than raw
organization data," which is exactly what P15's pattern already
guarantees: `get_tenant_benchmark_percentile` never returns another
organization's value, only a percentile band.

### The six new benchmark metrics

| Metric | Computed from |
|---|---|
| `kerrison_blood_finding_rate` | Blood findings ÷ inspections, for `instrument_type == "kerrison_rongeur"`, per tenant |
| `corrosion_trend` | Corrosion findings ÷ total inspections in the last 90 days, per tenant |
| `coverage_trend` | Average `Inspection.coverage_pct` in the last 90 days, per tenant |
| `repair_referral_rate` | `RepairRequest` count ÷ inspection count in the last 90 days, per tenant |
| `knowledge_maturity_index` | Approved ÷ total `KnowledgeArticle` count, per tenant |
| `training_maturity_index` | Average technician `training_progress_pct` (via `competency_service.technician_quality_dashboard`), per tenant |

Unlike `network_benchmark_service.compute_industry_benchmarks`, which
falls back to a seeded-random mock distribution when no
`IndustryBenchmark` row exists yet, every value here is a real per-tenant
rate — computed fresh from `InspectionFinding`/`Inspection`/
`RepairRequest`/`KnowledgeArticle` rows each time a benchmark is
requested. A tenant with no activity for a metric simply contributes no
value to that metric's distribution, rather than a fabricated one.

### Percentile bands, never raw values

`p25`/`p50`/`p75`/`p90`/`mean` are computed by sorting every contributing
tenant's real value and indexing into the sorted list (identical to
`network_benchmark_service.compute_industry_benchmarks`'s exact indexing
approach), then passed through `_add_laplace_noise` for differential
privacy. `get_tenant_benchmark_percentile` places one tenant's own real
value into a band (`below_p25`/`p25_to_p50`/`p50_to_p75`/`p75_to_p90`/
`above_p90`) against that noised distribution — the response never
contains any other organization's value, noised or otherwise.

### Suppression

If fewer than `MIN_FACILITIES` (5) organizations have contributed a value
for a metric, the entire benchmark for that metric is suppressed
(`suppressed: true`, all percentile fields `null`) — consistent with
every other k-anonymity gate across this codebase's four cross-tenant
intelligence systems.

## Federated Learning Signals (Section 4)

`horizon_federated_signal_service.py` computes six aggregate categories
using the stricter GSIN gate (`GLOBAL_K_THRESHOLD = 10`, imported from
`global_aggregation_job.py`, plus the same `_apply_laplace_noise`
differential-privacy helper) rather than P15's 5-facility floor, since
these are genuinely global (cross-organization, not domestic-network)
signals: finding frequency, anatomy trend, instrument failure pattern,
coverage effectiveness, supervisor agreement, and educational
effectiveness. Only organizations with an active federated sharing
agreement contribute to any of these — computed by scoping every
underlying query to
`horizon_participation_service.list_enrolled_tenant_ids(db)`.
