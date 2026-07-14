# Training Pipeline

**Status:** Extends the pre-existing "Phase 17" scaffold
(`app.services.ml.training_pipeline.prepare_training_run()`, which
deliberately stopped short of executing training because no labeled image
bytes existed yet) with a real, runnable execution step, now that real
labeled bytes can exist (opt-in `RetainedImage` rows).
**Code:** `backend/app/services/ml/training_execution.py`.
**Tests:** `backend/tests/test_dataset_registry.py::TestTrainingPipelineExecution`.

> The output of this program is **not** a better model. It is the
> infrastructure required to build trustworthy ones. The classifier trained
> here is a small, real, pure-Python foundation-scale baseline — not a
> clinically validated model, and it makes no such claim.

## Steps

| Step | Function |
|---|---|
| Load dataset | caller supplies `samples: list[dict]` (real image bytes + labels — e.g. from the dataset registry + `RetainedImage`) |
| Validate metadata | filters out samples missing `image_bytes`/`label` |
| Preprocess images | `app.services.ml.image_quality.assess_image_bytes()` → 3 real features (brightness, sharpness, aspect ratio); undecodable images are excluded, counted, never guessed |
| Split | `app.services.ml.dataset_split.split_dataset()` (reused, leakage-safe, stratified — unchanged from the pre-existing Section 7 implementation) |
| Train | a real, pure-Python logistic regression (gradient descent, deterministic — no random initialization or shuffling) |
| Validate / Evaluate | `app.services.ml.evaluation.evaluate()` (confusion matrix, precision/recall/F1, safety metrics — reused, not duplicated) on each split, plus `roc_curve()`/`roc_auc()` (new this pass) |
| Export model | the trained weight vector is returned in the run result |
| Register model | `build_registry_payload()` shapes the run into `ModelRegistryEntry` fields; the caller persists via `POST /api/model-pipeline/models/{id}/record-training-result` |

## Scope, by design

- **No new label taxonomy.** Trains a binary detector for one existing
  label from `app.services.ml.model_tasks.FINDING_LABELS` (default
  `"debris"|"none"`) — the same categories this platform's deployed
  scoring pipeline already targets (see the Core Inspection Workflow
  Closure sprint's `SUPPORTED_MODEL_CATEGORIES`).
- **No numpy/sklearn/torch dependency.** A small, real, interpretable
  logistic regression trained by hand-written gradient descent over three
  Pillow-computed features. `framework: "pure_python_baseline"` in the
  registry records this honestly rather than implying a heavier framework
  was used.
- **Deterministic and reproducible.** No randomness anywhere in the
  pipeline; the same `samples` + `seed` always produce the same split,
  weights, and metrics. `git_commit` is recorded automatically
  (`git rev-parse HEAD`) so a reviewer can reproduce the exact code that
  ran.
- **Honest about insufficient data.** Requires at least 3 real, decodable,
  labeled examples per class; below that (the common case in this
  repository today, since `RetainedImage` bytes are opt-in) the pipeline
  returns `training_status: "insufficient_data"` with zero fabricated
  metrics — the same honesty discipline `prepare_training_run()` already
  established for "no labeled dataset yet."

## Evaluation suite (Section 11)

`app.services.ml.evaluation` (pre-existing + this pass's additions):

- `confusion_matrix()`, `_per_class()` → precision/recall/F1/support/FPR/FNR
  per class (pre-existing).
- `safety_metrics()` → false-negative rates on safety-critical findings
  (blood/tissue/organic residue/crack/missing component) — the primary
  patient-safety risk metric (pre-existing).
- `evaluate()` → the full report, with optional per-group breakdowns
  (facility/instrument/etc. — pass any grouping via the `groups` param)
  (pre-existing).
- `roc_curve()` / `roc_auc()` → **new this pass**. Standard ROC (sorted
  thresholds, cumulative TPR/FPR) and trapezoidal-rule AUC, for a binary
  0/1 ground truth against continuous predicted scores. Distinct from
  `evaluate()`, which operates on discrete predicted labels. Returns
  `auc: None` with a clear note when `y_true` lacks both classes, rather
  than fabricating a curve.

## Relationship to the pre-existing scaffold

`app.services.ml.training_pipeline.prepare_training_run()` is untouched and
still the right entry point when no real image bytes exist yet — it
prepares and validates the split/leakage/task-definition machinery and
honestly records a `not_started` registry entry. `training_execution.
run_training_pipeline()` is the new, additional path for when real,
labeled, decodable image bytes ARE available.
