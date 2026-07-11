# Project Nova — Human-Agent Collaboration, Agent Marketplace & Observability

LumenAI Network v5.4, Sections 7, 8 & 9.

## Human-Agent Collaboration (Section 7)

`AgentCollaborationRequest` covers every action Section 7 names —
`assign_task`, `approve_work`, `reject_recommendation`,
`request_explanation`, `escalate_to_supervisor`. "Request explanations"
reuses GuardianX's `AIExplainabilityRecord`/
`guardianx_explainability_service.py` (v5.2) directly rather than a
second explanation store — a request of type `request_explanation`
simply references the explainability record it triggered.

A request filed as `escalate_to_supervisor` starts in an `escalated`
status immediately (not `pending`), since escalation is itself the
requester's action, not something awaiting a first decision; every
other request type starts `pending` and can be resolved to `approved`,
`rejected`, or `completed`.

```
POST /api/nova/collaboration-requests
POST /api/nova/collaboration-requests/{id}/resolve
GET  /api/nova/collaboration-requests/{id}
GET  /api/nova/collaboration-requests?agent_key=...&status=pending
```

## Agent Marketplace (Section 8) — zero new tables

Infinity's `MarketplaceListing`/`infinity_marketplace_service.py`
(v5.0) is already a generic, developer-owned, review-gated listing
pipeline. Nova extended `LISTING_TYPES` with 6 new agent-category
values (`inspection_agent`, `research_agent`, `manufacturer_agent`,
`education_agent`, `compliance_agent`, `simulation_agent`) — "Future
specialty agents" fold into the generic `MarketplaceListing` model with
no further schema change ever required.

```
GET /api/nova/marketplace/summary
```

## Observability (Section 9) — real metrics, honestly incomplete

Every metric is computed live from `AgentDefinition.health`/`status`,
`AgentMessage` counts, and `AgentTaskRun` outcomes. There is no latency
instrumentation, resource-usage telemetry, or retry mechanism anywhere
in this codebase for these in-process agents — rather than fabricate
those numbers, `GET /api/nova/observability/summary` reports them as
`{"available": false, "note": "..."}`, the same honesty discipline
Phase 22's own registry established ("not a fabricated uptime/latency
metric").

```
GET /api/nova/observability/summary
```

## No agent may act irreversibly without governance

Every `AgentTaskRun` and `AgentCollaborationRequest` carries
`human_review_required = True` by default. Nothing in this sprint
allows an agent's output to be auto-applied to a production record —
every named "Core Agent" only ever returns advisory data for a human
(or the existing Phase 22 Supervisor Agent) to act on.
