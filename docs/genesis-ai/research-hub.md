# Project Genesis AI — Global Learning Engine & Research Collaboration Hub

LumenAI Network v5.3, Sections 5 & 6.

## Global Learning Engine (Section 5) — zero new tables

Horizon's `horizon_federated_signal_service.py`/
`horizon_ai_improvement_service.py` (v3.4, Section 10) already aggregate
de-identified signals — finding frequency, anatomy trends, instrument
failure patterns, coverage effectiveness — and already generate
advisory hypotheses for human review
(`generate_improvement_suggestions`). Genesis AI reuses both directly.
"Model performance" and "Workflow effectiveness" reuse Phoenix's
`compute_ai_health_score`/`compute_workflow_health_score`
(`phoenix_platform_health_service.py`, v4.9) directly. "Knowledge
adoption" is the one genuinely new metric — how much of the knowledge
base is actually being viewed, not how healthy it is (Phoenix's
`compute_knowledge_health_score` already answers the latter).

```
GET /api/genesis-ai/learning-engine/summary
```

## Research Collaboration Hub (Section 6) — zero new tables

P20's `ResearchDataset`/`ResearchStudy`/`ResearchPublication`
(`p20_network_intelligence.py`) already implement governance-gated,
IRB-aware research proposals (`ResearchStudy.status == "proposed"`),
multi-center studies, benchmark datasets, academic collaboration
(`ResearchStudy.institution`), and publication tracking — already
composed by `horizon_research_portal_service.py` (v3.4). Genesis AI adds
exactly one thing: "participation is opt-in", via a new
`research_opt_in` column on P24's `AdvisoryConsortiumMember` (extended a
fourth time, after Beacon and Olympus's `observatory_opt_in` — a
deliberately *separate* flag, since an org may want its data in Global
Research Observatory trend rollups without opting into named research
studies, or vice versa).

```
GET   /api/genesis-ai/research-hub/summary
PATCH /api/genesis-ai/participants/{tenant_id}/research-opt-in
```
