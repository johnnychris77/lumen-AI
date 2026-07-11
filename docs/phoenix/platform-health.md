# Project Phoenix — Platform Health Dashboard

LumenAI OS v4.9, Section 7.

Frontend route `/platform-health`. Seven named health areas, each a real
composition — never a fabricated score — plus an Overall Platform
Maturity figure (the average of whichever areas have real data).

| Health area | Real source | Honest fallback |
|---|---|---|
| AI Health | `phoenix_ai_observatory_service` (agreement rate, drift) | "insufficient data" if no supervisor reviews exist |
| Knowledge Health | `knowledge_governance_service` + Knowledge Evolution Center | "insufficient data" if no articles exist |
| Workflow Health | `phoenix_workflow_optimization_service` (duration, failures, bottlenecks) | "insufficient data" if no executions exist |
| Digital Twin Health | `digital_twin_engine.compute_twin_dashboard` (utilization, open alerts) — the *instrument-flow* twin, distinct from Apollo's Quality Digital Twin | "insufficient data" if the twin is unavailable for the tenant |
| Security Health | `TenantMembership` enabled ratio + `TenantSubscriptionP14.hipaa_baa_signed_at` | "insufficient data" if no memberships exist |
| Integration Health | `ExternalSystemConnector` connection-status ratio | "insufficient data" if no connectors are configured |
| Quality Health | The most recent Apollo `QualityTwinSnapshot.overall_score` (read-only — never recomputes one, since a health-check dashboard should not have a write side effect) | "insufficient data" if no snapshot has been recorded yet |

```
GET /api/phoenix/platform-health/dashboard
```

Every score is bounded 0-100 and derived from a documented, real formula
— never a black-box number. Areas with genuinely no data report
`"insufficient data"` rather than defaulting to a fabricated midpoint.
