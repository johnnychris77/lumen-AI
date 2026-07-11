# Project Nova — Agent Registry & Core Agents

LumenAI Network v5.4, Sections 2 & 4.

## Agent Registry (Section 2) — the complete picture, not a partial one

`GET /api/nova/agents` merges two sources:

* Nova's own `AgentDefinition` rows (the 14 named Core Agents, seeded via
  `POST /api/nova/agents/seed-core`).
* Phase 22's live `app.agents.registry.get_registry()` (the 10
  pre-existing pipeline agents) — read directly, never re-derived or
  copied into a second table.

```
POST  /api/nova/agents/seed-core
GET   /api/nova/agents
GET   /api/nova/agents/{agent_key}
PATCH /api/nova/agents/{agent_key}/status
```

## Core Agents (Section 4) — 14 named, each a real wrapper

| Core Agent | `wrapped_module` |
|---|---|
| Inspection Agent | `app.agents.orchestrator` (Phase 22) |
| Vision Agent | `app.ai.inference` |
| Anatomy Agent | `app.agents.anatomy_agent` (Phase 22) |
| Digital Twin Agent | `app.services.digital_twin_engine` |
| Knowledge Agent | `app.services.athena_memory_service` |
| Clinical Reasoning Agent | `app.agents.clinical_reasoning_agent` (Phase 22) |
| Workflow Agent | `app.services.forge_workflow_service` |
| Simulation Agent | `app.services.simulation_engine_service` |
| Quality Agent | `app.services.apollo_executive_quality_service` |
| CAPA Agent | `app.services.apollo_capa_engine_service` |
| Audit Agent | `app.services.audit_chain_verification_service` |
| Executive Agent | `app.services.vanguard_executive_intelligence_service` |
| Research Agent | `app.services.genesis_ai_research_hub_service` |
| Enterprise Agent | `app.agents.enterprise_agent` (Phase 22) |

`POST /api/nova/agents/{agent_key}/invoke` dispatches to the real
wrapped service for the agents with a tenant-scoped summary function
(Digital Twin, Knowledge, Workflow, Quality, CAPA, Audit, Executive,
Research). For agents that are already real Phase 22 pipeline classes,
or that require inputs a generic endpoint can't reasonably supply
(Inspection needs a real inspection id; Vision needs real image bytes;
Simulation needs a real inspection id), this endpoint returns an honest
reference to where that agent is actually invoked — never a fabricated
result.

```
POST /api/nova/agents/{agent_key}/invoke
```
