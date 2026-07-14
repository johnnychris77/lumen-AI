# Success Metrics

**Status:** New this pass (Advisor). **Code:**
`backend/app/services/advisory_success_metrics_service.py`.
**API:** `GET /api/advisory-pilot/success-metrics`.

## Reused, not reimplemented

Every metric below composes an existing, already-reviewed computation
rather than re-deriving one:

| §10 metric | Source | Reuse |
|---|---|---|
| Reduction in repeat inspections | `quality_dashboard_service.benchmark()` | `reclean_rate_pct` current-vs-previous-month comparison, already built |
| Inspection consistency | Same | `pass_rate_pct` trend |
| Supervisor workload | Same | `supervisor_override_rate_pct` trend |
| System availability | `pulse_ai_ops_service.ai_operations_monitor()` | real `model_availability_pct` (errored/total real inspections), not a fabricated uptime number |
| Operational reliability | Same | `model_drift_detected`, reusing `sentinel_ai_health_service._detect_drift()` |
| User satisfaction | `advisory_user_feedback_service.feedback_summary()` | the overall per-dimension averages |

## Genuinely new this pass

`reduction_in_missed_findings` — a month-over-month false-negative-rate
comparison over real `SupervisorReview` rows, using the exact same
current-vs-previous-month split `quality_dashboard_service.benchmark()`
already established as this codebase's pattern for trend metrics (no new
mechanism, just applied to a metric `benchmark()` didn't already track).

## Honesty discipline

Every trend is `"insufficient_data"` when either comparison period has no
qualifying rows — never a fabricated improvement or regression. There is
no synthetic baseline; "reduction" always means a real month-over-month
comparison of real, already-recorded data.

## Time savings

Time-to-decision and turnaround are already tracked in full by
`advisory_workflow_impact_service.impact_summary()`
(`sla_monitoring_service.sla_monitoring()`) — reported there rather than
duplicated into this module; `WORKFLOW_IMPACT` evidence and
`SUCCESS_METRICS` evidence are read together, not merged into one
service, since they answer different questions (how the workflow
behaves vs. whether outcomes improved).
