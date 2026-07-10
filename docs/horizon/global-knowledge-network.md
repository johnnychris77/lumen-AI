# Project Horizon — Global Knowledge Network

LumenAI v3.4 — Sections 2, 3 & 6

## There is no prior "Project Cortex"

The sprint brief asks to "Extend Project Cortex" for the Global Knowledge
Graph. A full-repository search (`grep -ri cortex`) found no model,
service, route, or doc anywhere in this codebase named "Cortex" — the
closest existing system is the strictly per-tenant Knowledge Graph
(`app/services/knowledge_graph_service.py`, internally "Phase 21" — SPD
Clinical Knowledge Graph & Clinical Reasoning Engine). This document uses
"Cortex" only because the sprint brief does; the code and every other doc
in `docs/horizon/` refer to it as what it actually is: the existing Phase
21 reasoning engine.

## Local → Enterprise → Global

`horizon_knowledge_graph_service.py` implements the three-layer hierarchy
the sprint asks for, each layer built from what already exists wherever
possible:

- **Local** (`local_graph_summary`) — calls the existing per-tenant
  `knowledge_graph_service.explore()`/`learning_confidence()` directly.
  Nothing recomputed; every organization's local knowledge graph remains
  exactly as private and tenant-scoped as it always was.
- **Enterprise** (`enterprise_graph_reference`) — no new code needed.
  Atlas's `atlas_dashboard_service.enterprise_dashboard` already rolls up
  one health system's own facilities — the same finding Atlas's own
  Section 1 reached about the organization hierarchy applies here to the
  knowledge-graph layer.
- **Global** (`compute_global_knowledge_graph`) — genuinely new:
  aggregates real `InspectionFinding` observations (instrument type → zone
  → finding type) across every organization with an active federated
  sharing agreement, using the existing `NODE_TYPES`/`RELATIONSHIP_TYPES`
  taxonomy from `knowledge_graph_service.py` (e.g. the `"Zone HAS Common
  Findings"` relationship) rather than inventing a parallel vocabulary.
  Every edge is gated by `GLOBAL_K_THRESHOLD` (imported from
  `global_aggregation_job.py`) before publication.

Every organization retains ownership of its local knowledge graph — the
Global layer only ever aggregates counts of (instrument type, zone,
finding type) observations; a tenant's underlying inspection records are
never read by any other organization, and the Global layer cannot be used
to reconstruct any one organization's own data (below the k-anonymity
floor, nothing publishes at all).

## Knowledge Contribution Workflow (Section 3)

`horizon_contribution_service.py` is deliberately distinct from Atlas's
`atlas_knowledge_sharing_service.py`. Atlas shares an already-approved
`KnowledgeArticle` *within one health system's own facilities*
(`system_id`-scoped — every facility already belongs to the same
customer). Project Horizon shares content *across unrelated
organizations* — tenants with no relationship to each other — so
de-identification here means hiding the contributing organization's
identity from every other organization, not merely formatting a copy for
internal distribution.

Six contribution types (anatomy guidance, best practices, supervisor-
approved recommendations, Digital Twin insights, failure patterns,
educational content) all share one approval workflow
(`draft`/`pending_review`/`approved`/`rejected`/`archived` — the same
string values as `app/models/knowledge.py`'s `KnowledgeArticle` states,
kept intentionally separate rather than importing them, so a federated
cross-tenant table's lifecycle is never coupled to a tenant-scoped one).
Every contribution starts `pending_review` — nothing is auto-published.

### Versioning

A revision to an already-decided (approved or rejected) contribution
creates a **new row** with an incremented `version` and a
`supersedes_ref`/`superseded_by_ref` link back to the prior version —
history is never mutated in place. `GET /contributions/{ref}/versions`
walks the chain from its root and returns every version in order, still
de-identified (no `source_tenant_id` in the version history response).

## Emerging Trend Detection (Section 6)

`horizon_trend_detection_service.py` detects five trend types (new
corrosion pattern, new contamination location, unexpected anatomy risk,
manufacturer-specific quality trend, emerging inspection challenge) that
recur across `EARLY_WARNING_K` or more *unrelated organizations* — a
different axis from Atlas's `ENTERPRISE_WATCHLIST_EMERGING_TREND`
(`atlas_watchlist_service.py`), which only recurs within one health
system's own facilities. Every detected trend writes the full list of
currently-enrolled tenant IDs into `notified_tenant_ids_json` —
"notify participating organizations" is a literal, queryable field on
the alert itself, and each organization can retrieve its own personalized
feed (`GET /emerging-trends?mine_only=true`) or acknowledge a trend
(`POST /emerging-trends/{id}/acknowledge`).
