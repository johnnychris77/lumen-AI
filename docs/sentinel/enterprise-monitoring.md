# Sentinel Intelligence Engine — Enterprise Monitoring

LumenAI v3.0 · Project Sentinel

## The orchestrator

`sentinel_engine_service.run_sentinel_scan(db, tenant_id)` is the single
entry point (`POST /api/sentinel/scan`) that runs every monitor in
sequence — the way a scheduled job would:

1. Detect risk signals (Continuous Risk Monitor)
2. Refresh Clinical Watchlists
3. Monitor Digital Twins
4. Compute the AI Health / Enterprise Risk Score snapshot
5. Generate Enterprise Alerts from whatever the above found
6. Generate Recommendations from whatever the above found

Each step is independently callable and independently tested — the
orchestrator only sequences them; none of the actual detection logic lives
in `sentinel_engine_service.py` itself.

## What "monitor X" maps to concretely

| Sprint responsibility | Implementation |
|---|---|
| Monitor inspection workflows | `sentinel_risk_monitor_service` reads `InspectionFinding`/`Inspection` rows |
| Monitor Digital Twins | `sentinel_digital_twin_monitor_service` reads `instrument_condition_service.instrument_condition_history` |
| Monitor Knowledge Graph updates | `sentinel_dashboard_service.knowledge_growth_trend`, snapshotting `knowledge_graph_service.learning_confidence` over time |
| Monitor AI confidence | `sentinel_ai_health_service.compute_ai_health` |
| Monitor supervisor overrides | `sentinel_risk_monitor_service` reads `DispositionOverride` |
| Monitor recurring findings | `sentinel_risk_monitor_service`'s finding-type signals |
| Monitor anatomy trends | `sentinel_watchlist_service` via `anatomy_risk_service.anatomy_risk_dashboard` |
| Monitor enterprise KPIs | `sentinel_dashboard_service.executive_sentinel_dashboard` |

## Restricted to leadership roles

Every generation/scan endpoint (`/scan`, `/risk-signals/detect`,
`/watchlist/refresh`, `/digital-twin-flags/monitor`, `/recommendations/
generate`, `/alerts/generate`, `/dashboard`, `/ai-health`) requires
`admin`/`spd_manager`. Read endpoints for already-generated signals/
watchlist/recommendations/alerts are open to all authenticated roles
(`admin`, `spd_manager`, `operator`, `viewer`) so technicians and operators
can see what Sentinel has already found.
