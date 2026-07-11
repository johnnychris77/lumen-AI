# Project Nova — Agent Framework

LumenAI Network v5.4, Section 1.

## A real multi-agent pipeline already exists

Before writing any code, `app/agents/*.py` was read in full: a real,
working "Phase 22 — Multi-Agent Clinical Intelligence Platform" with 10
deterministic, in-process agent classes (Instrument, Anatomy, Coverage,
Contamination, Damage, Clinical Reasoning, Recommendation, Supervisor,
Learning, Enterprise), a static registry (`app.agents.registry.get_registry`),
and an orchestrator (`app.agents.orchestrator.run_pipeline`), already
exposed at `/api/agents/registry`, `/api/agents/run/{id}`,
`/api/agents/trace/{id}`. Nova does not rewrite, replace, or duplicate
any of it — those endpoints, and the frontend `/agent-trace` page, are
completely unchanged by this sprint.

## Every agent field the brief names is real

Every `AgentDefinition` row (`app/models/nova_agent_platform.py`) carries:

| Brief field | Column |
|---|---|
| Identity | `agent_key` |
| Role | `role` |
| Capabilities | `capabilities_json` |
| Memory | `AgentMemoryEntry` rows, keyed by `agent_key` (Section 6) |
| Permissions | `permissions_json` |
| Communication | `AgentMessage` rows (Section 3) |
| Goals | `goals_json` |
| Observability | computed live (Section 9), never a fabricated metric |
| Health | `health`, the same import-success check Phase 22 established |
| Version | `version` |

## No autonomous LLM agents

**This platform's "AI" remains entirely deterministic.** Every Nova
agent's `wrapped_module` names a real, pre-existing service this
codebase already built — Digital Twin engine, Athena's knowledge
memory, Forge's workflow service, Apollo's quality/CAPA engines, the
audit chain verifier, Vanguard's executive intelligence, Genesis AI's
research hub — never a call to an external LLM or embedding API. "Agent"
here means a governed, named, registry-tracked wrapper around
deterministic logic, exactly matching Phase 22's own documented
philosophy: "these agents are deterministic in-process Python wrapping
existing services, not external calls."
