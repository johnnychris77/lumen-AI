# Model Card Template

**Status:** New this pass — no model-card generator existed anywhere in
this codebase before it. **Code:** `backend/app/services/ml/model_card.py`
(`generate_model_card()`). **API:**
`POST /api/model-pipeline/models/{id}/generate-model-card`.
**Tests:** `backend/tests/test_dataset_registry.py::TestModelRegistryAndCard`.

Every section below is derived directly from `ModelRegistryEntry` fields
and the model's task definition (`app.services.ml.model_tasks`) — nothing
about performance or scope is asserted beyond what the registry itself
records. Generating a card requires no new input; it is a pure function of
existing registry data.

## Template

```markdown
# Model Card — {model_id} ({model_version})

**Approval status:** {approval_status}
**Training status:** {training_status}

## Purpose
{task name} — task key `{model_type}`.

## Supported findings
{the task's full label space, e.g. blood, bone, tissue, ... for "finding"}

## Unsupported findings
Any finding/category outside this task's label space is not evaluated by
this model.

## Training data
- Dataset version: `{dataset_version}`
- Dataset registry version ID: {dataset_version_id}

## Architecture & framework
- Architecture: {architecture}
- Framework: {framework}
- Hyperparameters: `{hyperparameters JSON}`
- Git commit: `{git_commit}`

## Performance
- Training metrics: `{training_metrics JSON}`
- Validation/evaluation metrics: `{evaluation_metrics JSON}`

## Known limitations
{known_limitations, or "None recorded."}

## Known failure modes
Safety-critical false-negative rates (missed contamination/structural
findings) are tracked separately — see
`app.services.ml.evaluation.safety_metrics` — and are the primary safety
risk for this model class.

## Ethical considerations
No causation or clinical-outcome claims are made. Output is always
advisory; `human_review_required` is always true regardless of approval
status.

## Clinical limitations
No FDA/regulatory clearance is claimed. This model may not drive a
clinical recommendation unless its approval status is `validated`, and
even then a supervisor override is always available (see
`app.services.ml.deployment_gates`).

## Governance
- Documentation complete: {documentation_complete}
- Clinical review complete: {clinical_review_complete}
- Metrics approved: {metrics_approved}
```

## Why this shape

Every field maps 1:1 to a `ModelRegistryEntry` column or a
`model_tasks.MODEL_TASKS` lookup — a reviewer can trace every line of a
generated card back to exactly the code and data that produced it (the
Definition of Done for this program). The card is required, non-empty,
before `model_card_generated` can pass in the Section 12 promotion gate
(see `TRAINING_PIPELINE.md` / `MODEL_REGISTRY.md`).
