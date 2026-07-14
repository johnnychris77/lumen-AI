# Training Configuration

**Status:** New this pass (Genesis — Production Model Training, Scientific
Validation & Model Governance). **Code:**
`backend/app/services/ml/training_config.py` (`TrainingConfig`).
**Tests:** `backend/tests/test_candidate_model_training.py::TestReproducibility`.

Every training run is driven by an explicit, hashable `TrainingConfig` —
never implicit defaults scattered across code. Two runs with the same
config and the same samples produce byte-identical results.

## Fields

| Field | Meaning | Default |
|---|---|---|
| `seed` | Deterministic seed threaded through augmentation and dataset splitting | `42` |
| `optimizer` | `batch_gradient_descent` — the only optimizer this pure-Python pipeline implements | `batch_gradient_descent` |
| `learning_rate` | Gradient-descent step size | `0.3` |
| `scheduler` | `constant` — no learning-rate decay is implemented | `constant` |
| `epochs` | Full passes over the training split | `500` |
| `batch_size` | `0` = full-batch gradient descent (the only mode implemented) | `0` |
| `augmentation` | Tuple of augmentation names to apply — see `MODEL_TRAINING_GUIDE.md` | `("horizontal_flip", "brightness_jitter")` |
| `input_resolution` | Recorded for reproducibility; the feature extractor itself is resolution-independent (see `MODEL_TRAINING_GUIDE.md`) | `(300, 300)` |
| `loss_function` | `binary_cross_entropy_one_vs_rest` — the one-vs-rest multi-class strategy's per-class loss | `binary_cross_entropy_one_vs_rest` |
| `class_weighting` | `balanced` — recorded for reproducibility; the dataset integrity gate (Section 4) rejects a dataset whose class balance falls below a minimum ratio rather than reweighting a skewed one silently | `balanced` |
| `early_stopping_patience` | `0` = disabled; the pipeline always runs the full `epochs` count today | `0` |
| `device` | `cpu` — the only device this pure-Python pipeline supports; never overclaimed as GPU | `cpu` |

## Reproducibility

`TrainingConfig.config_hash()` is a SHA-256 fingerprint of every field
above. `app.services.ml.candidate_training.run_candidate_training()`
records this hash on every run (`config_hash` in the result, and
`training_run_id` on the persisted `ModelRegistryEntry`). Two runs against
the same samples with the same config produce:

- identical `weights_by_class` (no randomness anywhere: augmentation is
  seeded per-sample via SHA-256, not Python's `random` module; gradient
  descent starts from a fixed zero-vector, never a random initialization),
- identical `training_metrics` / `validation_metrics` / `evaluation_metrics`,
- identical `config_hash`.

This is verified directly by
`test_candidate_model_training.py::TestReproducibility::test_identical_seed_reproduces_identical_weights_and_metrics`.

## Honesty notes

- No GPU, no batching beyond full-batch, no learning-rate schedule, and no
  early stopping are implemented — the config records this explicitly
  rather than claiming capabilities this pure-Python foundation-scale
  pipeline does not have.
- `class_weighting: "balanced"` describes intent, not an implemented
  reweighting algorithm; see `TRAINING_CONFIGURATION.md`'s sibling
  `MODEL_TRAINING_GUIDE.md` for how class balance is actually enforced
  (reject-gate, not reweighting).
