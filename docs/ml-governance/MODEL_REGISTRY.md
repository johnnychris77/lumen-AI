# Model Registry

**Status:** Extended this pass (the registry itself — `ModelRegistryEntry`,
`/api/model-pipeline/models` — already existed from an earlier "Phase 17"
pass; this program adds the reproducibility and governance fields below).
**Code:** `backend/app/models/model_registry.py`,
`backend/app/routes/model_pipeline.py`.
**Tests:** `backend/tests/test_model_pipeline_phase17.py` (pre-existing),
`backend/tests/test_dataset_registry.py::TestModelRegistryAndCard` (new).

## Fields

The pre-existing fields (`model_id`, `model_version`, `model_type`,
`dataset_version`, `training_date`, `training_status`, `evaluation_metrics`,
`known_limitations`, `approval_status`, `approved_by`, `release_notes`) are
unchanged — see the original `docs/ai/model-registry.md`. New, additive
fields:

| Field | Column | Meaning |
|---|---|---|
| Architecture | `architecture` | e.g. `logistic_regression_pure_python` |
| Framework | `framework` | e.g. `pure_python_baseline` — this repo trains no numpy/sklearn/torch model; see `TRAINING_PIPELINE.md` |
| Hyperparameters | `hyperparameters` (JSON) | e.g. `{"epochs": 500, "learning_rate": 0.3}` |
| Git Commit | `git_commit` | the exact commit the training run executed against |
| Dataset Version (registry) | `dataset_version_id` | FK to `DatasetVersion.id` (the freezable entity — see `DATASET_REGISTRY.md`), distinct from the pre-existing free-text `dataset_version` |
| Training Metrics | `training_metrics` (JSON) | metrics on the training split — distinct from `evaluation_metrics`, which reports validation/test |
| Documentation Complete | `documentation_complete` | human-recorded flag, never defaulted true |
| Clinical Review Complete | `clinical_review_complete` | human-recorded flag |
| Metrics Approved | `metrics_approved` | human-recorded flag |
| Model Card | `model_card_markdown` | the generated Model Card (see `MODEL_CARD_TEMPLATE.md`) |

## Rules (unchanged)

- A model is **always created as `experimental`** — the API hard-defaults
  it and never trusts a client-supplied status.
- Promotion is a separate, human-gated action; models are never
  auto-promoted.
- Registration, training-result recording, model-card generation, and
  governance-flag changes are all audit-logged.

## New endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/model-pipeline/models/{id}/record-training-result` | attach a real training run's outcome (architecture, framework, hyperparameters, git commit, metrics) |
| `POST` | `/api/model-pipeline/models/{id}/generate-model-card` | generate and persist the Model Card |
| `PATCH` | `/api/model-pipeline/models/{id}/governance-flags` | record documentation/clinical-review/metrics-approval sign-off |
| `GET` | `/api/model-pipeline/models/{id}/promotion-readiness?target_stage=` | read-only preview of the full Section 12 gate — see `TRAINING_PIPELINE.md` |

The pre-existing `POST /api/model-pipeline/models/{id}/promote` endpoint and
its underlying `app.services.ml.deployment_gates.evaluate_promotion()` are
**unchanged** — the new Section 12 gate (`app.services.ml.model_promotion.
evaluate_full_promotion_readiness()`) is an additive, separately-callable
layer, not a replacement, so existing promotion behavior and its tests are
unaffected. A deployment process may choose to require
`promotion-readiness.allowed == true` before ever calling `/promote`.

## Tenancy

Registry rows are tenant-scoped; a tenant only sees and promotes its own
models (unchanged from the original design).
