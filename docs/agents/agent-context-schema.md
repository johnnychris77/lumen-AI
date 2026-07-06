# Agent Context Objects

`app/agents/context.py` defines every typed context object the pipeline
passes between agents. All are pydantic `BaseModel`s — structure and
serialization only, no business logic lives on these classes themselves.

**Rule:** agents communicate only through these objects. No agent reads a
raw frontend request payload, a raw SQLAlchemy row, or another agent's
internal state directly — only the orchestrator touches the database on
the pipeline's behalf, and it always hands the next agent a typed context,
never the raw row (with two narrow, explicit exceptions noted below).

## Context objects

| Context | Produced by | Key fields |
|---|---|---|
| `InstrumentContext` | Instrument Intelligence Agent | `instrument_type`, `manufacturer`, `model`, `instrument_family`, `instrument_category`, `anatomy_zones`, `high_risk_zones`, `ifu_reference`, `digital_twin_available`, `profile_found`, `warning` |
| `AnatomyContext` | Anatomy Intelligence Agent | `instrument_family`, `anatomy_zones`, `required_zones`, `high_retention_zones`, `inspected_zones` (nullable — `None` means not tagged), `missing_zones`, `inspection_completeness` (nullable) |
| `CoverageContext` | Inspection Coverage Agent | `coverage_pct`, `required_images`, `missing_images`, `coverage_quality`, `capture_guidance` |
| `ContaminationContext` | Contamination Detection Agent | `findings: list[ContaminationFinding]`, `has_contamination` |
| `ContaminationFinding` | (nested) | `finding_type`, `probability`, `severity`, `confidence`, `zone`, `clinical_significance` |
| `DamageContext` | Damage Detection Agent | `findings: list[DamageFinding]`, `has_damage` |
| `DamageFinding` | (nested) | `finding_type`, `severity`, `repair_recommendation`, `trend` |
| `ClinicalReasoningContext` | Clinical Reasoning Agent | `interpretation`, `reasoning_chain` (list of ontology-chain steps — see `docs/knowledge-graph/reasoning-engine.md`), `risk_level`, `risk_score` |
| `RecommendationContext` | Recommendation Agent | `readiness_state` (one of the six Phase 20 states), `repair_candidate`, `explanation`, `human_review_required` |
| `SupervisorContext` | Supervisor Agent | `review_exists`, `agreement`, `corrections`, `override_action`, `ground_truth_label`, `training_label_created` |
| `LearningContext` | Continuous Learning Agent | `knowledge_confidence`, `reasoning_confidence`, `clinical_recommendation_confidence`, `zone_confidence`, `sample_sizes`, `note` |
| `EnterpriseContext` | Enterprise Intelligence Agent | `facility`, `facility_readiness_rate`, `most_common_contamination_type`, `highest_risk_anatomy_zone`, `note` |
| `AgentTraceEntry` | Orchestrator | `agent`, `version`, `input_summary`, `output_summary` — one per pipeline step, the Explainable Agent Trace's unit of record |

## Narrow, explicit exceptions

Three agents legitimately need something beyond the previous agent's
context, and take it as an explicit extra parameter rather than smuggling
it through a context object that shouldn't own it:

- **Recommendation Agent** takes the real `Inspection` row alongside the
  `ClinicalReasoningContext`, because the actual readiness classification
  (`classify_readiness()`, Phase 20) is keyed off the inspection's
  persisted `recommended_action`/`risk_score`/`score_status` — re-deriving
  those into a context field the Clinical Reasoning Agent would have to
  own redundantly would duplicate data ownership, not simplify it.
- **Supervisor Agent** takes `db` and `inspection_id` directly, because
  its entire job is a read-only lookup against `SupervisorReview` /
  `PilotValidationCase` — there's no upstream context that should carry a
  "has this been reviewed" flag, since that's this agent's own
  responsibility to determine.
- **Continuous Learning Agent** and **Enterprise Intelligence Agent** take
  `db` and `tenant_id` directly for the same reason — they aggregate
  across the tenant's full dataset, not just the one inspection flowing
  through the pipeline.

These are documented exceptions, not a loophole — every other agent
receives *only* typed context objects from its predecessors.

## Why pydantic

Every context object is a pydantic `BaseModel`, matching the convention
already used for every API request/response schema in this codebase
(`app/schemas/*.py`). This gives:

- Free `.model_dump()` serialization for the Explainable Agent Trace and
  the `/api/agents/run/{id}` response.
- Type validation at construction time — an agent that tries to hand off
  a malformed context fails immediately, not silently downstream.
