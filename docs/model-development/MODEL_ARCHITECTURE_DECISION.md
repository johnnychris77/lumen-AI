# Model Architecture Decision — Project Lens

## Environment constraint (verified directly, not assumed)

`backend/requirements.txt` declares only `Pillow`. Direct import testing
in this environment's `.venv` (`/home/user/lumen-AI/.venv`, Python 3.11)
confirms `torch`, `tensorflow`, `onnxruntime`, `scikit-learn`, `numpy`, and
`opencv` (`cv2`) all raise `ModuleNotFoundError` — only `PIL` imports
successfully. `app/ai/inference.py`'s YOLO/`ultralytics` path is real code
but dormant for the same reason (no weights file, no `ultralytics`
installed). See `LIVE_INFERENCE_TRACE.md` Section 9 for the full trace.

## Why a CNN/transfer-learning backbone is not the right choice here

The spec's own guidance is to prefer transfer learning "appropriate for
the available dataset size" and to not select a complex architecture for
novelty. Given:

- No GPU/CNN-capable framework is installed or importable in this
  environment.
- The only real dataset available this sprint is this sprint's own
  46-image declared experimental run (`TRAINING_ELIGIBILITY_REPORT.md`) —
  far too small to meaningfully fine-tune any convolutional backbone even
  if one were installable.
- Introducing a new hard dependency (torch/tensorflow/onnxruntime) to
  train a handful of tiny synthetic images would be disproportionate
  infrastructure risk for zero real accuracy benefit at this scale.

## The decision

Continue and extend this codebase's own established, already-real pattern
(built in the prior Genesis sprint, `app.services.ml.training_execution`/
`candidate_training`): a **pure-Python, hierarchical, one-vs-rest logistic
regression** over real Pillow-computed image features (brightness mean,
Laplacian-style edge-variance sharpness, aspect ratio —
`training_execution._feature_vector()`, reused verbatim, not
reimplemented).

### Hierarchical structure (Sections 2/5)

- **Stage A** (image-quality gate): not a trained model — a deterministic
  rule over `image_quality.assess_image_bytes()`'s real, pixel-computed
  quality grade. No labeled "is this evaluable" dataset exists to train a
  classifier for this stage, and a rule over an already-validated real
  signal is more honest than fitting a model with no ground truth for it.
- **Stage B** (abnormality detector): a binary one-vs-rest logistic
  regression head (`no_observable_abnormality` vs. everything else).
- **Stage C** (category classifier): a multiclass one-vs-rest logistic
  regression head, trained only on Stage-B-abnormal samples, over
  whichever taxonomy categories have sufficient real evidence (Section 2's
  requirement — see `TRAINING_ELIGIBILITY_REPORT.md`).

Both trained stages reuse the exact training primitives already built and
tested in `training_execution.py`/`candidate_training.py`
(`_train_logistic_regression`, `_train_one_vs_rest`, `_predict_multiclass`)
— extracted into a single shared prediction function
(`lens_training_pipeline.predict_hierarchical_from_weights()`) used
identically by both training-time evaluation and the live inference
adapter, so a live prediction is provably the same computation the
registered evaluation metrics describe.

## Reproducibility

- Deterministic seeds (SHA-256-derived, `TrainingConfig.seed`).
- `TrainingConfig.config_hash()` fingerprints every knob that affects the
  outcome.
- Deterministic augmentation (`augmentation.augment_image_bytes()`, seeded
  per-sample, no Python `random` module).
- CPU-only (`TrainingConfig.device = "cpu"`, the only mode this pipeline
  implements — never overclaimed as GPU-capable).
- Every training run records `git_commit()` — the exact code state that
  produced it.

## What this is not

Not a clinically validated model. Not a learned-visual-feature CNN — a
linear classifier over 3 hand-engineered scalar features. This is
explicitly disclosed in every model card, registry entry, and result
contract this sprint produces.
