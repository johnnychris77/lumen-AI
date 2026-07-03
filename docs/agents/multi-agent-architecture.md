# Multi-Agent Clinical Intelligence Platform

## Objective

Move LumenAI from one monolithic scoring pass to a pipeline of specialized
agents, each owning a specific slice of SPD expertise, all operating on
the same Clinical Ontology (`docs/architecture/lumenai-clinical-ontology.md`)
and Clinical Knowledge Graph (`docs/knowledge-graph/`). No agent bypasses
that architecture.

## What "agent" means here

Every agent in this pipeline is a small, deterministic Python class that
wraps **existing, already-tested services** — `instrument_anatomy.py`,
`instrument_zones.py`, `inspection_coverage.py`, `clinical_mentor.py`,
`knowledge_graph_service.py`, `pre_sterilization_command_center_service.py`.
No agent introduces new detection logic, no agent calls an LLM, and no
agent is a black box. This is honest about the platform's current
capability level — consistent with Phase 17's model-lifecycle framing
("training not started," nothing fabricated) — while establishing the
*structure* specialized agents will eventually run inside, per
`docs/knowledge-graph/agent-architecture.md`'s planned agent boundaries.

This module is distinct from the pre-existing, unrelated
`app/agent/spd_agent.py` (a single-purpose legacy summary generator) — the
new package lives at `app/agents/` (plural) to avoid confusion.

## The pipeline

```
Image Acquisition
    ↓
Computer Vision (existing scoring engine — already ran before this pipeline)
    ↓
Instrument Intelligence Agent
    ↓
Anatomy Intelligence Agent
    ↓
Inspection Coverage Agent
    ↓
Contamination Detection Agent
    ↓
Damage Detection Agent
    ↓
Clinical Reasoning Agent
    ↓
Recommendation Agent
    ↓
Supervisor Agent
    ↓
Continuous Learning Agent
    ↓
Enterprise Intelligence Agent
```

Each arrow is a typed context object handoff — see
`docs/agents/agent-context-schema.md`. The orchestrator
(`app/agents/orchestrator.py`) runs this exact sequence for one real,
already-scored inspection; see `docs/agents/agent-orchestrator.md`.

## The ten agents

| # | Agent | Module | Owns |
|---|---|---|---|
| 1 | Instrument Intelligence Agent | `app/agents/instrument_agent.py` | Manufacturer/family/model/category resolution, anatomy profile load, IFU lookup, digital-twin availability check |
| 2 | Anatomy Intelligence Agent | `app/agents/anatomy_agent.py` | Anatomy zones, required views, high-retention areas, inspected/missing zones |
| 3 | Inspection Coverage Agent | `app/agents/coverage_agent.py` | Coverage %, missing images, capture guidance |
| 4 | Contamination Detection Agent | `app/agents/contamination_agent.py` | Blood, bone, tissue, organic residue, debris |
| 5 | Damage Detection Agent | `app/agents/damage_agent.py` | Rust, corrosion, crack, pitting, wear, missing component, insulation damage |
| 6 | Clinical Reasoning Agent | `app/agents/clinical_reasoning_agent.py` | Interpretation, reasoning chain, risk assessment |
| 7 | Recommendation Agent | `app/agents/recommendation_agent.py` | Packaging-readiness classification + explanation |
| 8 | Supervisor Agent | `app/agents/supervisor_agent.py` | Reports (never fabricates) human agreement/corrections/override/training-label status |
| 9 | Continuous Learning Agent | `app/agents/learning_agent.py` | Live knowledge/reasoning/recommendation/zone confidence |
| 10 | Enterprise Intelligence Agent | `app/agents/enterprise_agent.py` | Facility/manufacturer/contamination-type/zone aggregation |

Section 4 and 5's finding ownership split reflects the platform's real
finding-type taxonomy — contamination types are biological soil,
damage types are structural/mechanical — and the split makes each agent's
severity and remediation logic (reclean vs. repair/remove) unambiguous.

## Non-negotiable rules

1. **No agent bypasses the architecture.** Every agent's output must be
   traceable to the Clinical Ontology chain. An agent that invents a
   finding type, a zone name, or an outcome value outside the frozen
   five-value decision engine (`docs/architecture/lumenai-clinical-intelligence-architecture.md`
   Layer 7) is a bug, not a feature.
2. **Agents communicate only through typed context objects** — see
   `docs/agents/agent-context-schema.md`. No agent reads raw frontend
   state or an unstructured dict from another agent.
3. **The Supervisor Agent never fabricates a supervisor decision.** Human
   expertise is the final authority (Design Principle 4,
   `docs/architecture/design-principles.md`) — this agent is read-only.
4. **The Continuous Learning Agent never mutates a persisted model
   state.** It reports live-recomputed confidence, consistent with Phase
   21's `learning_confidence()`.
5. **Every agent's output carries `human_review_required` through to the
   final recommendation** — the pipeline never auto-disposes an
   instrument.

## Known current limitation

The Contamination and Damage Detection Agents currently read a single
persisted `detected_issue` field per `Inspection` row — the schema does
not yet store multiple simultaneous findings per inspection (a richer
per-KPI findings list exists only transiently in the scoring engine's live
response, not persisted). This means, for a real historical inspection,
at most one of the two agents will report a finding today. This is stated
honestly in both agents' module docstrings rather than papered over —
persisting multiple findings per inspection is future schema work, not a
Phase 22 deliverable.
