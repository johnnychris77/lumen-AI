# Training Configuration — Project Lens

## The one documented command (Section 7)

```bash
cd backend
RETAIN_INSPECTION_IMAGES=true PYTHONPATH=. python scripts/run_project_lens_training.py
```

No hidden notebook-only steps — every step (`generate_experimental_dataset`
→ `compute_training_eligibility` → `run_lens_training` →
`register_lens_model`) is a plain function call in
`backend/scripts/run_project_lens_training.py`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | (resolved by `app.db.session`) | target database |
| `TENANT_ID` | `default-tenant` | tenant scope |
| `MODEL_VERSION` | `0.1.0-experimental` | registry version string |
| `GENERATE_EXPERIMENTAL` | `1` | run the declared experimental generator first; `0` trains only against whatever real ACTIVE Ground Truth already exists |
| `SAMPLES_PER_CLASS` | `8` | experimental generator sample count per class |
| `SEED` | `42` | `TrainingConfig.seed` |
| `EPOCHS` | `500` | `TrainingConfig.epochs` |
| `LEARNING_RATE` | `0.3` | `TrainingConfig.learning_rate` |

## Captured run (this sprint's real, reproducible artifact)

Run parameters (from `TrainingConfig.to_dict()`, real output of this
sprint's actual run):

```json
{
  "seed": 42,
  "optimizer": "batch_gradient_descent",
  "learning_rate": 0.3,
  "scheduler": "constant",
  "epochs": 500,
  "batch_size": 0,
  "augmentation": ["horizontal_flip", "brightness_jitter"],
  "input_resolution": [300, 300],
  "loss_function": "binary_cross_entropy_one_vs_rest",
  "class_weighting": "balanced",
  "early_stopping_patience": 0,
  "device": "cpu"
}
```

- **Training run ID** (`config_hash()`): deterministic 16-hex-char
  fingerprint of the above, stored as `ModelRegistryEntry.training_run_id`.
- **Git commit:** recorded via `training_execution.git_commit()` at run
  time (`ModelRegistryEntry.git_commit`).
- **Dataset version:** `project-lens-experimental-v1`
  (`DatasetVersion.id = 1` in this run).
- **Dataset hash:** `training_run_id`'s `config_hash` already binds the
  configuration; the concrete sample set is bound by the (deduplicated)
  `image_sha256` values captured per sample in
  `TRAINING_ELIGIBILITY_REPORT.md`.
- **Split-manifest hash:** produced by `dataset_split.split_dataset()`'s
  own seeded hashing — reproducible from `seed` + the sample set.
- **Architecture:** `hierarchical_logistic_regression_one_vs_rest_pure_python`.
- **Pretrained weights source:** none — trained from scratch (linear
  models have no meaningful "pretrained" starting point).
- **Library versions:** Pillow only (`requirements.txt`); no numpy/torch/
  sklearn in this environment (see `MODEL_ARCHITECTURE_DECISION.md`).
- **Start/completion timestamps:** `run["trained_at"]`, an ISO-8601 UTC
  timestamp recorded at the moment training completed.

Class weights: `TrainingConfig.class_weighting = "balanced"` is recorded
as the declared policy; the pure-Python logistic-regression trainer itself
does not yet implement per-class loss reweighting (a disclosed limitation,
not a silent gap — see `KNOWN_LIMITATIONS.md`).
