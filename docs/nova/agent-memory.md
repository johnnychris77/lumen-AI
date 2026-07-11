# Project Nova — Agent Memory

LumenAI Network v5.4, Section 6.

## Governed and tenant-aware

`AgentMemoryEntry` is genuinely new — nothing in this codebase persists
a per-agent memory record. Every entry is scoped to both `agent_key` and
`tenant_id`; every read filters by both, never a cross-tenant memory
leak. `memory_type` covers every category Section 6 names:

| Brief item | `memory_type` |
|---|---|
| Working Memory | `working` |
| Conversation Context | `conversation_context` |
| Historical Learning | `historical_learning` |
| Task History | `task_history` |
| Evidence | `evidence` |

```
POST /api/nova/agents/{agent_key}/memory
GET  /api/nova/agents/{agent_key}/memory?memory_type=task_history
```

Memory here is a governed audit record, not a live conversational
context window for an LLM — consistent with this platform's
deterministic-agent design (`docs/nova/agent-framework.md`).
