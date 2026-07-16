# Model Training Guide

**Status:** New this pass (Genesis). **Code:**
`backend/app/services/ml/candidate_training.py`,
`backend/app/services/ml/augmentation.py`,
`backend/app/services/ml/dataset_integrity.py`.
**API:** `POST /api/dataset-registry/versions/{id}/run-candidate-training`.
**Tests:** `backend/tests/test_candidate_model_training.py`.

## Candidate model scope (Section 1)

This program does **not** attempt the complete inspection taxonomy. The
currently approved scope is:

- `debris`
- `corrosion`
- `no_actionable_finding` (the negative class — essential so the model
  learns "normal")
- `blood` — **only** if at least 3 validated samples exist for it
  (`app.services.ml.candidate_training.resolve_candidate_classes()`); if
  not, `blood` is simply never trained or scored, never fabricated.

Every other category in the broader taxonomy (bone, tissue, rust, crack,
pitting, insulation damage, missing component, etc. — see
`app.services.ml.model_tasks.FINDING_LABELS`) remains explicitly
**NOT EVALUATED** by this candidate pipeline. No probability is ever
reported for a category this pipeline does not train.

## Pipeline steps (Section 3), one call, no manual intervention

`POST /api/dataset-registry/versions/{id}/run-candidate-training` (or
`app.services.ml.candidate_training.run_full_candidate_pipeline()` directly)
runs every step below in a single call:

1. **Dataset validation** — `app.services.ml.dataset_integrity.
   validate_dataset()`: rejects the whole dataset (raises
   `DatasetInvalidError`, HTTP 422) if duplicates exist or facility/
   manufacturer/instrument diversity falls below the minimum — see
   `MODEL_VALIDATION_GUIDE.md`.
2. **Duplicate detection** — same reject-gate, by `image_sha256`.
3. **Preprocessing** — real, Pillow-computed features per image
   (brightness, sharpness/blur-proxy, aspect ratio —
   `app.services.ml.training_execution._feature_vector`, reused not
   duplicated).
4. **Augmentation** — `app.services.ml.augmentation.augment_image_bytes()`:
   deterministic horizontal flip + brightness jitter, seeded per
   `(config.seed, sample_id)` so the exact same augmented image is produced
   every run.
5. **Training** — one-vs-rest logistic regression (one real, pure-Python,
   gradient-descent-trained binary classifier per candidate class), reusing
   `app.services.ml.training_execution._train_logistic_regression`.
6. **Validation** — metrics computed on the validation split.
7. **Evaluation** — metrics computed on the held-out test split (Section
   5 — see `MODEL_VALIDATION_GUIDE.md`).
8. **Error analysis** — `app.services.ml.error_analysis.analyze_errors()`
   on the test (or validation, if no test split) predictions — see
   `ERROR_ANALYSIS.md`.
9. **Confidence calibration** — `app.services.ml.evaluation.
   calibration_report()` on the same split.
10. **Model export** — `export_artifact()` writes the trained weights +
    config + git commit to a JSON file (never pickle — no arbitrary-code-
    execution risk on load) under `model_artifacts/` (git-ignored; a real
    deployment would point this at durable, access-controlled storage).
11. **Model registration** — a `ModelRegistryEntry` row is always created —
    even an `insufficient_data` run is registered honestly (`candidate_stage`
    stays `Experimental`) rather than silently discarded.
12. **Model card generation** — `app.services.ml.model_card.
    generate_model_card()` is called and persisted automatically.

No step requires a human to intervene between 1 and 12 — the whole chain
runs inside one function call / one HTTP request.

## Insufficient data (honesty, not fabrication)

If fewer than 3 real, decodable, labeled images exist for any required
class, or the leakage-safe training split ends up with fewer than 2
classes, the pipeline returns `training_status: "insufficient_data"` with
every metric field explicitly `None` — never a fabricated number. This
mirrors the pre-existing honesty discipline in
`app.services.ml.training_pipeline.prepare_training_run()` and
`app.services.ml.training_execution.run_training_pipeline()`.

## Reproducibility

See `TRAINING_CONFIGURATION.md`. Two calls to `run_candidate_training()`
with the same samples and the same `TrainingConfig` produce byte-identical
`weights_by_class` and metrics.
