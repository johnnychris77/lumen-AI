# Project Horizon — Research Platform

LumenAI v3.4 — Section 7

## Composing what P20 already built

Before this sprint, P20's "Research Data Exchange"
(`app/models/p20_network_intelligence.py`, Phase 4) already implemented a
governance-gated, IRB-aware dataset release workflow: `ResearchDataset`
(`release_status`: draft/under_review/approved/released/withdrawn,
`governance_approved`, `irb_approval_number`, `k_floor`), `ResearchStudy`,
and `ResearchPublication` (`causation_claim_present` must be `False` for
governance clearance). Full CRUD for all three already exists under
`/api/network-intelligence/research/*`.

Project Horizon does not duplicate any of this. `horizon_research_portal_
service.py` only adds the **presentation layer** — a single composed
summary for the `/research` frontend page — reading P20's already-
released datasets, published studies, and cleared publications directly,
alongside Horizon's own new global signals, benchmarks, emerging trends,
and approved knowledge contributions.

## Endpoint

```
GET /api/horizon/research/portal
```

Returns:

```jsonc
{
  "global_trend_summaries": [ /* published FederatedLearningSignal rows */ ],
  "global_benchmarks": [ /* six horizon_benchmark_service metrics, percentile bands only */ ],
  "emerging_risks": [ /* EmergingTrendAlert rows */ ],
  "published_knowledge": [ /* approved KnowledgeContribution rows, de-identified */ ],
  "global_knowledge_graph": [ /* published GlobalKnowledgeGraphEdge rows */ ],
  "released_datasets": [ /* P20 ResearchDataset rows with release_status == "released" */ ],
  "research_studies": [ /* P20 ResearchStudy rows, active/completed/published */ ],
  "publications": [ /* P20 ResearchPublication rows, governance_cleared == true */ ],
  "human_review_required": true,
  "disclaimer": "..."
}
```

## What the sprint's Section 7 asks for, mapped

| Requirement | Source |
|---|---|
| Global trend summaries | `horizon_federated_signal_service.list_federated_signals` |
| Published knowledge | `horizon_contribution_service.list_contributions(approval_status=APPROVED)` |
| Emerging risks | `horizon_trend_detection_service.list_emerging_trends` |
| Inspection science | `global_knowledge_graph` (instrument → zone → finding relationships) |
| Anatomy research | Same graph, filterable by `source_node_type` |
| Instrument family research | `global_benchmarks` (per-instrument-type metrics) + P20's `ResearchDataset.instrument_categories` |

## Research datasets remain de-identified

Every field surfaced by `research_portal_summary` was already de-
identified by the service that produced it before this composition layer
ever sees it — `list_contributions` never includes `source_tenant_id`
for another organization's submission; every benchmark is a percentile
band, never a raw value; every federated signal and knowledge-graph edge
is k-anonymity-gated before it is ever marked `published`. The research
portal composition layer adds no new de-identification logic of its own
because none of the data it reads needs any — it was already safe to
publish by the time it reaches this module.
