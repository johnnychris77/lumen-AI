# Project Pulse — Command Center

LumenAI OS v4.2 — Section 1

## `/pulse` is additive, not a replacement for `/`

Before writing any frontend code, `frontend/src/main.tsx` was checked
for existing default-landing-page logic: `/` is a single static route
(`<Route path="/" element={<Page name="Dashboard"><Dashboard /></Page>} />`)
with no role-based branching or redirect machinery of any kind. Making
`/pulse` the new default for leadership would require adding new
branching logic to that one universal entry point — real new code
touching every user's landing experience, and a materially different
risk profile than every other page this branch has added. `/pulse` is
therefore a new, separate route alongside the unchanged `/`, consistent
with this branch's additive-only precedent across eleven prior sprints.

## The fourteen live widgets, mapped to their real source

`pulse_command_center_service.pulse_command_center` composes every named
widget from a service that already existed before Pulse (or from this
sprint's own new modules) — no widget recomputes a score another module
owns:

| Widget | Source |
|---|---|
| Enterprise Health | `sentinel_dashboard_service.run_sentinel_health_snapshot` (the one canonical `enterprise_risk_score`) |
| Facility Health | Genesis's `platform_org_service.facility_for_tenant` |
| Inspection Queue | Real `Inspection.score_status`/recent-count queries |
| AI Analysis Queue | Same queue count + `pulse_ai_ops_service`'s inference latency |
| Supervisor Queue | Real `Inspection.supervisor_review_required` backlog count |
| Repair Queue | `RepairRequest.status` in the same open-status set `insight_operational_forecast_service` already defines |
| Enterprise Alerts | This sprint's own `pulse_alert_service` (Section 5) |
| Digital Twin Health | `digital_twin_engine.compute_twin_dashboard` |
| Knowledge Growth | `knowledge_graph_service.learning_confidence` + recent `KnowledgeArticle` count |
| AI Model Health | This sprint's own `pulse_ai_ops_service` (Section 8), built on Sentinel's existing AI health engine |
| System Status | Genesis's `platform_module_registry_service.list_modules` |
| Integrations | Nexus's `nexus_registry_service.list_connectors` |
| Notifications | Genesis's `platform_notification_service.unified_notifications` |
| Recent Activity | Genesis's `platform_activity_feed_service.universal_activity_feed` |

## Endpoint

```
GET /api/pulse/command-center
```

Every field is computed fresh on each call — there is no background
refresh job and no stale cache to invalidate; "continuously update" /
"refresh automatically" (Section 4) means the frontend polls this (and
the section-specific) endpoints on an interval.
