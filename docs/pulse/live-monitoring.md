# Project Pulse — Live Monitoring

LumenAI OS v4.2 — Sections 3, 4, 6, 7, 8 & 9

## Enterprise Command Map (Section 3)

`pulse_map_service.py` composes Genesis's `platform_org_service.
organization_tree` (P16's existing hierarchy) with Atlas's existing
`atlas_dashboard_service.get_latest_facility_intelligence` scores. The
one genuinely new piece: `status_color_for_score` — no status-color
banding (green/yellow/orange/red/gray) existed anywhere in this codebase
before Pulse (confirmed: Atlas only exposes numeric scores). It is a
pure derived function over an existing score (higher `risk_score` is
worse, banded at 25/50/75), never a fabricated color; `None` (no data
yet) is always `gray`.

```
GET /api/pulse/map
GET /api/pulse/map/facilities/{system_id}/{facility_id}
```

## Live Operational KPIs (Section 4)

`pulse_kpi_service.live_kpis` computes ten metrics fresh from real rows
on every call (throughput, queue length, supervisor backlog, avg review
time, AI confidence, coverage %, high-risk findings, repair queue,
knowledge contributions, digital twin health, enterprise risk) — no
caching, no background job. `GET /api/pulse/kpis`.

## Executive Command Dashboard (Section 6)

`pulse_executive_service.executive_command_dashboard` is a pure
composition — Enterprise/Risk Score both read Sentinel's one canonical
`enterprise_risk_score` (confirmed: Atlas's own dashboard already reads
this same field rather than recomputing it); Quality Score reads the
same `quality_score_used` Sentinel's own risk computation already
derives; Education Health reads `competency_service.
technician_quality_dashboard`; Knowledge Health reads
`knowledge_graph_service.learning_confidence`; Digital Twin/Operational
Health both read `digital_twin_engine.compute_twin_dashboard`'s real
`utilization_pct`; Integration Health is computed from Nexus's connector
statuses; Forecast Summary reads Insight's existing
`forecast_operational`. `GET /api/pulse/executive`.

## Live Workflow Monitoring (Section 7)

`pulse_workflow_monitor_service.py` composes Forge's existing
`WorkflowExecution`/`WorkflowApprovalInstance` — current stage, waiting
state, blocking rule, and responsible user are all *derived* from an
execution's real `decision_path`/`execution_log` and any linked approval
instance, never stored as new columns. Because Forge's
`execute_workflow` runs synchronously to completion within one call, a
`running` status is only observable for the brief window between a
long execution's start and its finish — this is an honest property of
the underlying execution model, not a limitation Pulse works around.
`GET /api/pulse/workflow-monitor`, `GET /api/pulse/workflow-monitor/{execution_id}`.

## AI Operations Monitor (Section 8)

`pulse_ai_ops_service.py` reuses `sentinel_ai_health_service.
compute_ai_health` for confidence/agreement/false-positive/false-negative
rate and drift directly. It adds only what didn't exist before: model
version distribution and inference latency (both from real
`Inspection.model_version`/`inference_timestamp` columns) and a
confidence histogram (real `Inspection.ai_confidence` values bucketed).
**GPU/CPU utilization is honestly reported as `not_applicable`** —
confirmed nowhere in this codebase does any runtime hardware metric
exist; the CV pipeline is a deterministic, non-GPU inference gateway by
default. `GET /api/pulse/ai-ops`.

## Facility Command Console (Section 9)

`pulse_facility_console_service.facility_console` composes this
sprint's own KPI/alert services with Genesis's notification/activity
feeds, scoped to one tenant. `GET /api/pulse/facility-console`.
