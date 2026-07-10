# Project Catalyst — AI Skills Framework

LumenAI OS v4.4 — Section 10

## Every skill wraps a real, already-existing service

`catalyst_skills_service.py` defines eight independently callable,
independently testable functions. None of them computes anything new —
each is a thin, typed wrapper around a service this codebase already
had before this sprint:

| Skill key | Function | Wraps |
|---|---|---|
| `inspection` | `inspection_skill` | `Inspection`/`InspectionFinding` filtered query |
| `digital_twin` | `digital_twin_skill` | `digital_twin_engine.compute_twin_dashboard` |
| `knowledge_search` | `knowledge_search_skill` | `knowledge_graph_service.explore` + `knowledge_repository_service.list_articles` |
| `analytics` | `analytics_skill` | `anatomy_risk_service.anatomy_risk_dashboard` + `finding_trend_service.finding_trends` |
| `forecast` | `forecast_skill` | `insight_operational_forecast_service.forecast_operational` |
| `workflow` | `workflow_skill` | `forge_workflow_service.get_workflow`/`list_workflows`/`version_history` |
| `research` | `research_skill` | `knowledge_graph_service.reasoning_chain` |
| `reporting` | `reporting_skill` | `atlas_report_service.generate_executive_report` or `pulse_executive_service.executive_command_dashboard` |

`SKILL_DISPATCH` maps every `SKILL_CATEGORIES` entry to exactly one of
these functions (enforced by an `assert` at import time — a skill can
never be silently unregistered from its own catalog).

## Catalog vs. execution

`CatalystSkill` rows (seeded by `ensure_skills_seeded`) are a **catalog**
for discovery — `GET /api/catalyst/skills` returns the eight rows above
with their name/category/description — not the thing that actually runs
a skill. The functions in `SKILL_DISPATCH` are what execute; the catalog
exists so the copilot workspace (and any future admin UI) can list what
Catalyst is capable of without hardcoding it client-side.

## Independent testability

Each skill function takes `(db, tenant_id, **kwargs)` and returns a
plain dict — no dependency on `CatalystConversation`, the query engine,
or the action engine. `test_catalyst_copilot.py` calls each one directly
against seeded `Inspection`/`InspectionFinding`/`KnowledgeArticle` rows,
independent of the chat endpoint.
