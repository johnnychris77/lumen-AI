# Model Card (Genesis additions)

**Status:** Extends the pre-existing Model Card generator
(`docs/ml-governance/MODEL_CARD_TEMPLATE.md`, built in the Dataset Registry
& AI Model Development Foundation sprint) with the sections this program's
Section 10 additionally requires. The generator itself
(`app.services.ml.model_card.generate_model_card()`) is the same function,
extended additively — not a second, competing implementation.

## New sections this pass

| Section | Source |
|---|---|
| **Intended use** | Fixed, honest text: advisory input to a human SPD supervisor's review, never standalone/autonomous |
| **Out-of-scope use** | Fixed text enumerating what this model must not be used for (unsupported categories, autonomous decisions, pre-promotion-gate deployment, unrepresented instruments/facilities/conditions) |
| **Human oversight requirements** | Fixed text: human review is always required regardless of confidence or stage; supervisor override always available |
| **Version history** | One line per registry entry: model version, training run ID, registration timestamp, training status |
| **Confidence calibration** | Summary of `ModelRegistryEntry.calibration_report` — expected calibration error + recommended threshold |
| **Known failure modes** (extended) | Now includes the ranked failure modes from `ModelRegistryEntry.error_analysis_report`, in addition to the pre-existing safety-metrics note |
| **Governance** (extended) | Now includes `candidate_stage`, `clinical_review_status`, `error_analysis_reviewed`, `reproducible_training_confirmed`, `governance_review_completed`, `reviewer`, `deployment_status` — the full Section 11 checklist state, not just the Section 12 flags from the prior pass |

## Sections unchanged from the prior pass

Purpose, Supported findings, Unsupported findings, Training data,
Architecture & framework, Performance, Known limitations, Ethical
considerations, Clinical limitations — see `MODEL_CARD_TEMPLATE.md` for
the full original template and rationale.

## Candidate-pipeline models

Models registered via `app.services.ml.candidate_training.
run_full_candidate_pipeline()` use `model_type = "candidate_finding_
multiclass"`, which is not one of the static `app.services.ml.model_tasks.
MODEL_TASKS` entries. For these models, `generate_model_card()` derives
"Supported findings" from the actual evaluation report's per-class
breakdown (`eval_metrics["per_class"].keys()`) rather than a static task
label list — never guessed, always read from the real evaluation that ran.

## Generation

`POST /api/model-pipeline/models/{id}/generate-model-card` (manual
trigger, pre-existing) — but for candidate-pipeline models, the card is
also generated **automatically** as the final step of
`run_full_candidate_pipeline()`, satisfying Section 3's "no manual
intervention after training begins."

## Lumen Decision Engine addendum

The model itself is unchanged by the Lumen Decision Engine work — see
`docs/decision-engine/LUMEN_DECISION_ENGINE.md` for the architectural
separation this program formalized: the vision model (this card's
subject) only observes; baseline comparison, organizational policy
resolution, and the recommendation are all handled by separate, later
layers (`app/services/policy_resolution_service.py`,
`app/services/lumen_decision_engine.py`). "Supported findings" in this
card continues to be the single source of truth
(`SUPPORTED_MODEL_CATEGORIES`) for which observation-taxonomy categories
the Decision Engine is permitted to score — an unsupported signal is
never silently reported as a category; it opens an
`UnknownFindingReview` instead (`docs/decision-engine/UNKNOWN_FINDING_LEARNING_LOOP.md`).
