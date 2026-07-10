# Project Catalyst — Copilot Architecture

LumenAI OS v4.4 — AI Copilot & Natural Language Operations

## Naming disambiguation (read this first)

Before writing a single line of this sprint, the codebase was checked
for any existing use of the word "copilot" — and a real, pre-existing
system was found: **P9 "Autonomous Inspection Copilot"**
(`app/models/copilot.py` — `InspectionSession`, `InspectionStep`,
`CopilotRecommendation`, `InspectionProtocol`, `EscalationEvent`;
`app/services/copilot_engine.py`; `app/routes/copilot.py`, mounted at
`/api/copilot`). P9 is a guided, step-by-step inspection checklist and
escalation wizard driven by keyword-matched protocol templates — it has
no conversational or natural-language interface, and shares no models,
services, or routes with this sprint.

To avoid any collision:

| | P9 (existing) | Catalyst (this sprint) |
|---|---|---|
| API prefix | `/api/copilot` | `/api/catalyst` |
| Model prefix | `Copilot*` / `Inspection*` (checklist-scoped) | `Catalyst*` |
| Frontend route | none | `/copilot-workspace` |
| Nature | Guided checklist / escalation wizard | Conversational NL query + action engine |

This same table is the answer if a future sprint asks "is there already
a copilot?" — yes, two, and they do different things.

## No real LLM integration — and Catalyst does not add one

This codebase has zero real LLM/completion-API integration anywhere: no
`openai`/`anthropic` package dependency, no network call to a completion
endpoint. Every "AI" feature here — Sentinel's risk scoring, Insight's
forecasts, Beacon's cross-hospital correlation, Forge's rule engine — is
a deterministic, seeded, or statistical computation over real data.
Catalyst follows the same rule: its natural-language engine is a
deterministic keyword/intent classifier (`catalyst_query_engine.py`)
that dispatches to real service functions. It never simulates, stubs, or
fabricates a live LLM call. If this project later integrates a real LLM
provider, that is a distinct, explicitly-scoped future change — not
something this sprint pretends already exists.

## Layer map

```
frontend/src/components/CatalystCopilotWorkspace.tsx   (chat UI, 6 side panels)
frontend/src/pages/CopilotWorkspacePage.tsx             (/copilot-workspace)
        │
        ▼  fetch (@/lib/api)
app/routes/catalyst_copilot.py                          (/api/catalyst/*)
        │
        ├── catalyst_conversation_service.py    — Section 9 memory
        ├── catalyst_query_engine.py            — Section 2 NL queries
        ├── catalyst_action_engine.py           — Section 3 NL actions
        ├── catalyst_persona_service.py         — Sections 4-6 personas
        ├── catalyst_explainability_service.py  — Section 7 evidence envelope
        └── catalyst_skills_service.py          — Section 10 skills registry
                │
                ▼  calls into (never duplicates) already-existing services
        pulse_kpi_service, pulse_executive_service, atlas_report_service,
        digital_twin_engine, anatomy_risk_service, finding_trend_service,
        forge_action_service, forge_workflow_service, capa_service,
        knowledge_graph_service, knowledge_repository_service,
        competency_service, insight_operational_forecast_service
```

## New tables (`app/models/catalyst_copilot.py`)

* `CatalystConversation` — a chat session, scoped by `(tenant_id, user_email)`.
* `CatalystMessage` — one turn, carrying its explainability trace inline.
* `CatalystSkill` — the AI Skills Framework catalog.
* `CatalystPendingAction` — a short-lived (15-minute) confirm-token row
  gating any critical natural-language action.

No other new tables were added — this sprint is a natural-language front
door over a dozen sprints' worth of already-real services, not a second
copy of any of them.
