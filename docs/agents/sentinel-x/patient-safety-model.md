# Project Sentinel-X — Patient Safety Watch, Predictive Risk & Supervisor Workspace

LumenAI AI Specialist, Sections 5, 8, 10, 13.

## Patient Safety Watch (Section 5)

`sentinelx_patient_safety_watch_service.scan_for_alerts` fires proactive
alerts only from real, repeated patterns (never a single event) across
already-persisted `SentinelXRiskAssessment` rows: repeat contamination,
repeat corrosion, repeat repair, repeat anatomy failures, high-risk
instruments, and escalating Digital Twins. `SentinelXPatientSafetyAlert` is
a new table, deliberately distinct from the pre-existing `SentinelAlert`
(Project Sentinel v3.0).

## Predictive Risk (Section 8)

`sentinelx_predictive_service.py` produces five named forecasts (escalating
corrosion, repeat blood findings, inspection backlog risk, high-risk
workflows, recurring anatomy failures) as **deterministic trend
extrapolation over real signal** — never a trained forecasting model. Every
forecast states its `confidence` and its `assumptions` explicitly, so it is
never mistaken for a statistically validated prediction.

## Supervisor Workspace (Section 10)

`sentinelx_supervisor_workspace_service.supervisor_workspace_summary`
surfaces the highest-risk inspections/instruments, pending reviews,
critical anatomy zones, escalating trends, and recommended priorities —
all derived from real, already-persisted assessments.

## Auditable Supervisor Override (Sections 10, 13)

Sentinel-X's own risk level is always advisory. `sentinelx_override_service.
submit_override` requires a non-empty `rationale` (raises otherwise) and
persists an append-only `SentinelXSupervisorOverride` row — it never
mutates the original assessment's `risk_level`/`risk_score`, so both the
AI's original determination and the supervisor's override remain
independently auditable.

## API

```
GET  /api/sentinelx/predictive/{instrument_identity}
GET  /api/sentinelx/supervisor-workspace
POST /api/sentinelx/overrides
GET  /api/sentinelx/overrides/{assessment_id}
```
