# Project Nova — Agent Communication Bus & Task Orchestration

LumenAI Network v5.4, Sections 3 & 5.

## Agent Communication Bus (Section 3) — every interaction is logged

`AgentMessage` is genuinely new — Phase 22's `run_pipeline` already
builds an in-memory `trace` list per real inspection run but never
persists it. `nova_communication_bus_service.log_pipeline_trace` is a
thin adapter that persists those *real* trace entries as `AgentMessage`
rows, never a re-derivation of the pipeline's own reasoning. Nova's own
Task Orchestration (below) logs a message on every step advance too.

```
GET /api/nova/messages?agent_key=knowledge_agent
```

## Task Orchestration (Section 5) — configurable, distinct from Phase 22

`AgentTaskRun` is a configurable ordered pipeline of `agent_key`s,
distinct from Phase 22's hardcoded 10-step inspection pipeline (which
keeps its own `run_pipeline` entry point unchanged, reachable at
`/api/agents/run/{inspection_id}`). A task run tracks
`current_step_index`, a `step_log`, and a terminal `status`
(`running`/`completed`/`failed`).

```
POST /api/nova/task-runs
POST /api/nova/task-runs/{id}/advance
POST /api/nova/task-runs/{id}/fail
GET  /api/nova/task-runs/{id}
GET  /api/nova/task-runs?status=running
```

Example pipeline matching Section 5's brief:

```json
{
  "pipeline_name": "image-to-recommendation",
  "agent_sequence": [
    "vision_agent", "anatomy_agent", "knowledge_agent", "digital_twin_agent",
    "quality_agent", "clinical_reasoning_agent", "audit_agent"
  ]
}
```

Every `advance` call logs an `AgentMessage` from the current step's
agent to the next, so a task run's full reasoning trail is always
reconstructable via `GET /api/nova/messages`.
