# Project Catalyst — Natural Language Query & Action Engines

LumenAI OS v4.4 — Sections 2 & 3

## Query Engine (Section 2)

`catalyst_query_engine.py::answer_query(db, tenant_id, query)` classifies
free text into one of eight intents by keyword match — no ML model, no
external API call, fully deterministic and unit-testable — then
dispatches to the real skill function that already computes that answer:

| Example query | Intent | Dispatches to |
|---|---|---|
| "How many instruments are awaiting supervisor review?" | `supervisor_backlog` | `pulse_kpi_service.live_kpis` (`supervisor_backlog` field) |
| "Give me the executive summary for this week." | `executive_summary` | `catalyst_skills_service.reporting_skill` (Atlas report or live Pulse dashboard) |
| "Which Digital Twins are showing declining health?" | `digital_twin_health` | `digital_twin_engine.compute_twin_dashboard` |
| "What's our contamination rate by anatomy zone?" | `anatomy_contamination` | `anatomy_risk_service.anatomy_risk_dashboard` |
| "Show me recurring corrosion findings." | `recurring_finding_trend` | `finding_trend_service.finding_trends` |
| "Which Kerrisons had blood findings this week?" | `instrument_finding_search` | direct `Inspection`/`InspectionFinding` filtered query |
| "What's the workload forecast for next week?" | `forecast` | `insight_operational_forecast_service.forecast_operational` |
| "Find the knowledge article about flexible endoscopes." | `knowledge_search` | `knowledge_repository_service.list_articles` + `knowledge_graph_service.explore` |

Every branch returns the same shape: `{intent, skill_used, answer, data,
evidence}` — `evidence` is always the Section 7 explainability envelope
(see `explainability.md` note in `copilot-architecture.md`), never
omitted.

An unmatched query returns `intent: "unknown"` with a confidence of
`0.0` and a helpful list of what the engine *can* answer — never a
guessed or fabricated answer to a query it didn't actually understand.

## Action Engine (Section 3)

`catalyst_action_engine.py` never invents a second execution path for
any action — every one of the nine action types calls a real,
already-existing service:

| Action | Reuses | Confirmation required? |
|---|---|---|
| `assign_inspection` | `forge_action_service.execute_action("assign_technician")` | Yes |
| `create_capa_draft` | `capa_service.create_capa(status="draft")` | Yes |
| `notify_supervisor` | `forge_action_service.execute_action("notify_supervisor")` | Yes |
| `schedule_competency_review` | `forge_action_service.execute_action("require_supervisor_review")` | Yes |
| `publish_workflow` | `forge_workflow_service.publish_workflow` | Yes |
| `generate_report` | `catalyst_skills_service.reporting_skill` | No (read-derived) |
| `export_dashboard` | live KPI/executive dashboard → CSV | No (read-derived) |
| `open_digital_twin` | `digital_twin_engine.compute_twin_dashboard` | No (navigation) |
| `open_knowledge_article` | `knowledge_repository_service.get_article` | No (navigation) |

### Why "schedule a competency review" doesn't create a calendar entry

No calendar/scheduling infrastructure exists anywhere in this codebase
(confirmed before writing this action). Rather than fabricate one,
`schedule_competency_review` raises a real supervisor-review
notification (the same `require_supervisor_review` mechanism Forge's
workflow engine already uses) tagged with the technician's name — the
honest existing way to get a human to actually schedule that review.

### Confirmation gate

Every action in the "Yes" column above goes through
`CatalystPendingAction`: `propose_action` creates a row with a
`secrets.token_urlsafe(24)` confirm token and a 15-minute expiry;
nothing executes until `confirm_action` is called with that exact
token, scoped to the same `(tenant_id, user_email)` that proposed it.
This is deliberately lighter-weight than Forge's multi-step
`WorkflowApprovalInstance` chain — Catalyst only ever gates one action
behind one explicit "yes," which is what "confirmation required for
critical actions" actually asks for.

```
POST /api/catalyst/actions/propose  {action_type, params, conversation_id}
  -> {requires_confirmation: true, confirm_token, summary, expires_at}
POST /api/catalyst/actions/confirm  {confirm_token}
  -> {action_type, result}
POST /api/catalyst/actions/cancel   {confirm_token}
  -> {action_type, status: "cancelled"}
GET  /api/catalyst/actions/pending
  -> {pending_actions: [...]}   # backs the workspace's Open Tasks panel
```
