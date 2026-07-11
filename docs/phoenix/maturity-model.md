# Project Phoenix — Platform Maturity Index

LumenAI OS v4.9, Section 10.

## No re-derivation of Apollo's Quality Maturity Index

Apollo's `apollo_quality_twin_service.compute_quality_twin` (v4.7) is
already an 8-dimension "Quality Maturity Index." Phoenix's 9-dimension
Platform Maturity Index takes that composite's `overall_score` as its own
**Quality** dimension input, rather than re-deriving CAPA/competency/
audit-readiness numbers a third time.

## The nine dimensions

| Dimension | Real source |
|---|---|
| Inspection | % of inspections with a real AI confidence score (`phoenix_ai_observatory_service.coverage_summary`) |
| Knowledge | Approved-article ratio minus a penalty for duplicates/contradictions/outdated guidance (Platform Health's Knowledge Health) |
| Quality | Apollo's Quality Digital Twin `overall_score` (most recent snapshot) |
| Workflow | Platform Health's Workflow Health (execution failures + approval bottlenecks) |
| Analytics | A bounded knowledge-query usage-activity proxy (`KnowledgeQueryLog` volume) — explicitly documented as a usage signal, not a benchmarked maturity level |
| Education | Org-average technician `training_progress_pct` (`competency_service.technician_quality_dashboard`) |
| Digital Twins | Platform Health's Digital Twin Health (instrument-flow twin utilization + open alerts) |
| Governance | Enabled-vs-total `RetentionPolicy` ratio (`vanguard_governance_service.governance_dashboard`) |
| Executive Intelligence | Audit-readiness `overall_readiness_score` (same governance dashboard) |

`overall_score` is the average of whichever dimensions have real data —
a tenant with zero workflow executions or zero external connectors isn't
penalized for missing data; that dimension is simply excluded from the
average rather than scored as zero.

## Progression over time

Every computation persists a `PlatformMaturitySnapshot` row, so maturity
progression is a real historical series, not a single point-in-time
number:

```
POST /api/phoenix/maturity/compute
GET  /api/phoenix/maturity/history
```

Every snapshot's `factors` field documents exactly which real
composition or proxy backs each of the nine scores.
