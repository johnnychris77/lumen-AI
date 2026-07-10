# Project Athena — Institutional Memory Engine

LumenAI OS v4.8, Sections 1, 2, 6, 7 & 9.

## Naming disambiguation

Before writing any Athena code, every existing knowledge-adjacent surface
was read in full — this codebase already had an extensive institutional-
knowledge ecosystem before Athena:

| Concern | Pre-existing system | Athena's relationship to it |
|---|---|---|
| `/api/knowledge` prefix | `app/routes/knowledge.py` (v1.8) | Athena mounts at `/api/athena` instead |
| `/api/knowledge-graph` prefix | `app/routes/knowledge_graph.py` | Untouched |
| Institutional knowledge store | `KnowledgeArticle`/`ClinicalCase` (v1.8) | Athena composes, adds only 2 new categories + 1 column |
| Approval workflow | `knowledge_governance_service.py` | Reused directly, unchanged |
| Knowledge search | `knowledge_search_service.smart_search` | Extended (widened source coverage) in `athena_search_service.py` |
| AI Q&A | `ai_knowledge_assistant_service.answer_question` | Extended with 3 new query shapes in `athena_assistant_service.py` |
| Knowledge analytics | `knowledge_analytics_service.py` | Extended with 4 new curator checks |
| Clinical Playbooks | `workflow_forge.py`'s `WorkflowDefinition` | Reused directly — no parallel model |
| Knowledge Graph | `knowledge_graph_service.py` | Composed for the Experience Graph's Finding/Instrument/Anatomy/Recommendation segments |

## Institutional Memory Engine (Section 1)

`athena_memory_service.py` normalizes real records from six pre-existing
stores into one searchable "memory entry" shape — no new "memory" table:

| Memory type | Real source |
|---|---|
| Clinical decisions / lessons learned / vendor & repair observations | `KnowledgeArticle` (2 new categories added: `vendor_observation`, `repair_observation` — everything else already had a category) |
| CAPA outcomes | `capa_lifecycle_service.list_capas` |
| Root Cause Analyses | `RootCauseAssignment` |
| Workflow improvements | `ContinuousImprovementInitiative` |
| Policy history | `QualityPolicy` (Apollo, v4.7) |
| Education history | `CompetencyEvent` (education_completed/annual_competency/procedure_validation) |

```
GET  /api/athena/memory/entries?source_types=knowledge_article,capa,...
GET  /api/athena/memory/search?q=...
GET  /api/athena/memory/summary
```

## Expert Knowledge Capture (Section 2)

`KnowledgeArticle`'s existing `approval_status` (draft → pending_review →
approved/rejected → archived) and `knowledge_governance_service.py`
already implement the full approval workflow — a submission from
`POST /api/athena/expert-contributions` enters exactly the same pipeline
as any other article. The one new capability is photo/video/voice
attachments via `KnowledgeMediaAttachment` (source_type=
`knowledge_article`), since no media field existed on `KnowledgeArticle`
before Athena.

```
POST /api/athena/expert-contributions
POST /api/athena/expert-contributions/{id}/media
GET  /api/athena/expert-contributions/{id}/media
```

## AI Knowledge Curator (Section 6)

`athena_curator_service.py` extends `knowledge_analytics_service.py`'s
existing pattern with four new, entirely deterministic checks:

* **Duplicate candidates** — title+body token-overlap (Jaccard similarity) between article pairs.
* **Outdated guidance** — approved articles never reviewed, or not reviewed within a configurable staleness window.
* **Retirement candidates** — outdated *and* zero views (a conservative, real signal — never auto-archived).
* **Emerging best practices** — repeated `knowledge_contribution` topics (Apollo's `CompetencyEvent` log) with no matching article yet.

Every suggestion is for human review; nothing archives, merges, or
demotes an article automatically.

```
GET /api/athena/curator/summary
```

## Organizational Search (Section 7)

No embeddings/vector search/TF-IDF exists anywhere in this codebase
(confirmed by grep) — consistent with the platform-wide "deterministic,
source-grounded, zero real LLM integration" convention.
`athena_search_service.organizational_search` federates keyword search
across Knowledge Articles/Cases (via the existing `smart_search`),
Policies, CAPAs, Digital Twins, Inspections, Playbooks, Research
(publications), and Competencies — each result tagged with its real
source system. "Meeting Notes" has no backing store anywhere in this
codebase; rather than fabricate one, that source always returns an empty
result with an honest reason string.

```
GET /api/athena/search?q=...
```

## Athena Assistant (Section 9)

`athena_assistant_service.ask_athena` extends `ai_knowledge_assistant_
service.answer_question` (unchanged, still the grounded baseline answer)
with three new query shapes:

| Example question | Dispatches to |
|---|---|
| "Show me how we handled recurring corrosion..." | `athena_memory_timeline_service.build_memory_timeline` |
| "Find all lessons learned related to..." | `athena_search_service.organizational_search`, filtered to `lesson_learned` |
| "What changed in our IFU guidance over the past year?" | `apollo_policy_service.list_policies` (version/review-date history) |
| "Compare our current workflow with last year's" | `forge_workflow_service.version_history` |

```
POST /api/athena/assistant/ask
```
