# AI Governance Framework

Consolidates the AI governance controls already built across Phases 17,
18, 21, and 23 into the topic checklist an enterprise buyer's AI
governance/compliance reviewer needs.

## Model Lifecycle

Data → Labels → Training → Evaluation → Registry → Shadow Mode → Pilot →
Validation → Deployment (`docs/ai/model-training-pipeline.md`). No model
auto-promotes between stages — every promotion requires a human-approved
checklist including a minimum sample size
(`app/services/ml/deployment_gates.py`).

## Dataset Governance

- `docs/ai/model-training-dataset-plan.md`,
  `docs/ai/lumenai-dataset-versioning-plan.md` — versioned, stratified,
  leakage-free training/eval/test splits (`app/services/ml/dataset_split.py`)
- Every dataset version is referenced by both `ModelRegistryEntry` and
  Phase 18's `PilotValidationCase.dataset_version`

## Supervisor Validation

- Every AI recommendation is advisory; a supervisor's agreement,
  correction, or override is what determines actual disposition
  (`app/models/supervisor_review.py`, Design Principle 4)
- One supervisor submission creates the review record, the Phase 18
  ground-truth label, and the Phase 23 Clinical Decision Ledger entry —
  see `docs/agents/multi-agent-architecture.md` and
  `docs/cios/clinical-decision-ledger.md`

## Model Approval Process

- `docs/ai/model-deployment-gates.md` — capabilities per stage:
  experimental cannot drive or advise (shadow-only); pilot is advisory
  with a mandatory disclaimer; validated may support a decision with
  supervisor override; deprecated is unusable
- Registration always starts `experimental` (server-hardened —
  `app/models/model_registry.py`)

## Shadow Mode

- `docs/ai/shadow-mode-validation.md` — a candidate model runs silently,
  reconciled against the human's actual decision, before it ever drives
  or advises anything (`app/models/shadow_prediction.py`)
- Shadow responses never surface the predicted label as a recommendation

## Versioning

- Every inspection/decision references seven governed versions
  (architecture, ontology, knowledge graph, model, dataset, clinical
  rule, inspection pipeline) — see `docs/cios/platform-governance.md`
- A `ClinicalDecisionLedgerEntry` snapshots the versions active when it
  was written and is never retroactively updated

## Clinical Rule Management

- `docs/cios/clinical-rule-registry.md` — every enforced clinical rule is
  registered with an ID, purpose, evidence pointer, priority, version, and
  approval status. No rule is documented without corresponding real
  enforcement code.

## Knowledge Graph Governance

- `docs/knowledge-graph/spd-clinical-knowledge-graph.md` — the node/
  relationship taxonomy is versioned (`knowledge_graph_version` in
  platform governance) and every reasoning-chain output is traceable to
  a real function, never a black box

## Continuous Learning

- `docs/knowledge-graph/reasoning-engine.md` §Continuous Knowledge
  Learning, and `app/services/knowledge_graph_service.py::learning_confidence` —
  confidence signals are recomputed live from real supervisor reviews on
  every request; nothing here mutates a persisted model state or
  fabricates a training event
- `docs/agents/multi-agent-architecture.md`'s Continuous Learning Agent
  is explicitly read-only for the same reason

## Architecture Governance

- `docs/architecture/` (Phase 19.5) — the frozen reference architecture;
  every new AI capability must pass the enforcement checklist
  (`docs/architecture/architecture-enforcement-checklist.md`) before
  shipping

## What this framework guarantees

No AI model in LumenAI can reach production influence over a clinical
decision without: passing through the registry, clearing the deployment
gate's human-approved checklist, being validated in shadow mode against
real outcomes, and remaining subject to supervisor override at all times.
This is enforced in code (`app/services/ml/deployment_gates.py`), not
just asserted in this document.
