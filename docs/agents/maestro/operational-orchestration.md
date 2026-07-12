# Project Maestro — Operational Orchestration

LumenAI AI Specialist, Mission & Section 1.

## Naming disambiguation

**"Orchestrator"/"orchestration" already exists** as two unrelated,
pre-existing systems in this codebase:

- Phase 22's `app/agents/orchestrator.py` (`run_pipeline(db, inspection,
  tenant_id)`) — the hardcoded 10-step per-inspection Vision/Anatomy/
  Clinical Reasoning agent pipeline, computed live and never cached.
- Nova's `nova_orchestration_service.py` — `AgentTaskRun`, Nova's own
  configurable ordered pipeline of `agent_key`s for its task platform.

Maestro is a **different, higher-level concept**: an executive layer that
reads the *outputs* of every specialist (including both systems above) to
rank operational priorities for SPD leadership. `maestro_orchestration_
service.py` never touches or extends either existing orchestration system.
`/maestro` and `/api/maestro` were unclaimed before this sprint.

## What Maestro does

Rather than presenting dozens of dashboards, Maestro answers the most
important leadership question: **"What should I do first today, and
why?"** It is a pure read-and-synthesize layer over every other LumenAI
specialist — it never replaces human leadership. Every recommendation is
explainable, evidence-based, auditable, role-aware, and subject to human
approval (`human_review_required` is always `True`).

## Architecture

```
Sentinel-X (risk)  ─┐
Vulcan (reliability)├─► Priority Engine ─► Leadership Recommendation Engine ─► Decision Journal
Sage (education)    │        │                        │
Veritas (evidence)  │        ▼                        ▼
Aegis (process)     │  Operational Health      Daily Operational Brief
Phoenix (maturity)  │      Index                       │
Pulse (live ops)    │                                  ▼
Forge/CAPA          ┘                          Leadership Workspace (/maestro)
```

## What is composed vs. genuinely new

Maestro composes real, already-computed specialist output — it never
re-derives a score another module already owns:

| Signal | Reused from |
|---|---|
| Vision/Anatomy/Clinical Reasoning | `app.agents.orchestrator.run_pipeline` (Phase 22) |
| Knowledge | `knowledge_graph_service.learning_confidence` |
| Digital Twin | `instrument_condition_service.instrument_condition_history` |
| Evidence integrity | `veritas_evidence_agent_service.run_evidence_assessment` |
| Process variation | `vulcan_aegis_integration_service.compute_process_variation_signal` |
| Instrument reliability | `vulcan_reliability_agent_service.run_reliability_assessment` |
| Education gaps | `sage_knowledge_gap_service.list_gaps` / `sage_learning_plan_service.list_plans` |
| Clinical risk | `sentinelx_risk_agent_service.run_risk_assessment` / `sentinelx_dashboard_service.risk_dashboard_summary` / `sentinelx_supervisor_workspace_service.supervisor_workspace_summary` |
| Live operations | `pulse_command_center_service.pulse_command_center` |
| Platform maturity | `phoenix_maturity_index_service.compute_platform_maturity_index` |
| Approval workflow | `forge_approval_service` |
| CAPA drafting | `capa_suggestion_service.generate_capa_suggestions` / `create_capa_from_suggestion` |
| Conversational Q&A (read-only reference) | Catalyst's `catalyst_query_engine.answer_query` — Maestro never calls it directly |

Five tables are genuinely new: `MaestroPriorityItem`, `MaestroRecommendation`,
`MaestroDailyBrief`, `MaestroOperationalHealthSnapshot`,
`MaestroDecisionJournalEntry`. The Strategy Timeline (Section 6) is a pure
query over `MaestroRecommendation`, not a separate table.

## Deterministic, not an autonomous LLM

`maestro_orchestration_service.run_daily_orchestration` is a deterministic
Python function that calls the Priority Engine, the Recommendation Engine,
the Health Index, and the Daily Brief generator in sequence. There is no
LLM/embedding API call anywhere in Maestro.

## API

Prefix `/api/maestro`. Key endpoint: `POST /api/maestro/run` (runs the full
daily orchestration); `GET /api/maestro/workspace` (the `/maestro`
Leadership Workspace payload).

## Frontend

Route `/maestro` — `MaestroLeadershipWorkspace.tsx`, showing Top
Priorities, Operational Health, Open Risks, Today's Recommendations,
Pending Executive Decisions, Shift Readiness, and Enterprise Status.
