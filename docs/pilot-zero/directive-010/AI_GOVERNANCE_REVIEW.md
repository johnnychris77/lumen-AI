# LPZ-DIR-010 — AI Governance Review (AGR)

**Purpose:** verify the AI-governance framework (Directive 009) and its status.
Evidence-based.

## Review items

| Item | Framework (Directive 009) | Implementation | Status |
|---|---|---|---|
| **Experiment governance** | `EXPERIMENT_GOVERNANCE_STANDARD.md` | `training_config`, `candidate_training`; first-class Experiment record is a gap | ⚠️ Framework; record gap |
| **Model registry** | `MODEL_REGISTRY_STANDARD.md` | `ModelRegistryEntry` (checksum, lineage, card, governance flags) | ✅ Framework + code |
| **Model versioning** | `MODEL_VERSIONING_STANDARD.md` | `model_version`; parent/rollback-ref pointers are a gap | ⚠️ Framework; pointer gap |
| **Evaluation standards** | `MODEL_EVALUATION_STANDARD.md` (methodology; no thresholds) | `ml.evaluation`, `ml.error_analysis`, calibration | ✅ Framework + code |
| **Promotion lifecycle** | `MODEL_PROMOTION_STANDARD.md` | `candidate_promotion` 5-stage ladder + gates | ✅ Framework + code |
| **Rollback strategy** | `MODEL_ROLLBACK_STANDARD.md` | versioned entries + checksum; rollback event is a gap | ⚠️ Framework; event gap |
| **Bias monitoring plan** | `AI_GOVERNANCE_STANDARD.md` (stratified) | evaluation supports stratification | ✅ Plan defined |
| **Drift monitoring plan** | `AI_GOVERNANCE_STANDARD.md` | Shadow/Advisor drift & monitoring services | ✅ Plan + substrate |
| **Human review requirements** | Model family + governance standards | decision-support-only, fail-closed patterns | ✅ Defined |

*Note:* Directive 009 documentation is on an open PR at review time (SRR-2); this
review assesses the framework as authored.

## Findings

* **AGR-1 (framework strong):** The candidate-model governance framework is complete
  and largely backed by an existing model registry, evaluation/error-analysis
  services, and a promotion ladder with shadow/pilot-evidence gates.
* **AGR-2 (enforcement gap):** First-class Experiment records, author≠reviewer
  separation of duties, rollback-reference/event, and pinned GT/baseline/evaluation
  versions are **documented, not enforced in code**. **Condition** (shared with
  ERR-2).
* **AGR-3 (no model yet):** No candidate vision model has been trained, registered,
  or evaluated under Pilot Zero (correctly — Directive 009 forbids training). There
  is therefore no model instance to govern operationally yet; this is expected.
* **AGR-4 (safety posture):** Decision-support-only, human-supervised, fail-closed,
  no-deployment posture is consistently specified and aligns with the platform's
  contamination-safety invariants.

## AGR determination

**CONDITIONAL PASS.** The AI-governance framework is comprehensive and safety-first,
with strong existing substrate. Conditions: merge Directive 009 (SRR-2), enforce the
High-priority AI-governance gates in code (AGR-2), and — when authorized — validate
the framework against the first governed experiment (AGR-3). No AI is deployed;
posture is correct for Pilot Zero.
