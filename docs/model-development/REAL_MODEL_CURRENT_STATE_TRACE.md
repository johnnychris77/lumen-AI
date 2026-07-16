# Real Model Current-State Trace — Project Vision Sprint 2

Written before any Sprint 2 edits, per the mission's "inspect and reuse"
requirement. This sprint's mission is, almost in full, already implemented
by **Project Lens Sprint 4** (`docs/model-development/FIRST_MODEL_SCOPE.md`
and neighboring docs) — this trace documents exactly what already exists so
Sprint 2 extends it precisely rather than rebuilding it.

## 1. Exact placeholder inference path

Two independent placeholder/legacy-model code paths exist, both predating
Project Lens:

- **`app.ai.inference.LumenAIModel`** — a YOLO-based wrapper. When no real
  YOLO weights file exists at `LUMENAI_MODEL_PATH` (the shipped default),
  `predict()` falls back to `_deterministic_fallback()` — a SHA-256-seeded
  pseudo-random result, not real computer vision. `SUPPORTED_MODEL_CATEGORIES
  = ("debris", "corrosion")` documents which categories this path is
  considered to cover; `app.ai.inference_status.get_inference_status()`
  gives a live (not static) answer to whether real weights are actually
  present in a given deployment.
- **`app.services.baseline_comparison_scoring_service.analyze_inspection()`**
  — the primary scoring function every inspection submission calls. Its own
  docstring/log line states plainly: `"INFERENCE MODE: deterministic
  placeholder active — not a trained CV model"`. It seeds a
  SHA-256-derived pseudo-random number per KPI (`_seed_from`/`_pseudo`) for
  every `CONTAMINATION_KPIS + CONDITION_KPIS` entry, producing
  `predicted_findings`/`kpi_summary`/`model_result` — the contract every
  existing consumer (Decision Engine, reports, dashboards, frontend) reads.
  Per the false-PASS remediation (`FALSE_PASS_ROOT_CAUSE.md`), undeclared
  **cleaning** KPI findings (blood/bone/tissue/organic residue/debris) are
  now marked `evaluated: false` and the disposition layer reports
  `AI_ANALYSIS_UNAVAILABLE` rather than treating the placeholder's low
  pseudo-random number as a verified "clean" result. **Condition KPIs
  (corrosion, rust, crack, etc.) and any declared finding still use the
  placeholder's scored probability unconditionally** — this remains true
  after this sprint's changes (see Section 9 below for the new, explicit,
  opt-in production gate this sprint adds on top, not in place of, that
  disclosed behavior).

## 2. Current training implementation (Project Lens, already built)

`app.services.ml.lens_training_pipeline.run_lens_training()` — a real,
deterministic, pure-Python hierarchical pipeline:

- **Stage A (image quality)** is explicitly *not* a trained classifier —
  every sample reaching training already passed the real, pixel-computed
  `image_quality.assess_image_bytes()` gate at ingestion; Stage A's
  abstention outcome is applied by the live adapter at inference time.
- **Stage B (abnormality)** — binary one-vs-rest logistic regression
  (`training_execution._train_logistic_regression`) over real
  Pillow-computed features (`training_execution._feature_vector`:
  brightness/sharpness/aspect ratio).
- **Stage C (category)** — multiclass one-vs-rest
  (`candidate_training._train_one_vs_rest`) over abnormal-only samples.
- Leakage-safe split: `dataset_split.split_dataset(..., group_by_serial=True)`
  grouped by real, barcode/UDI-backed Digital Twin identity
  (`lens_training_pipeline._to_split_sample` — an `untracked:` Digital
  Twin ID, meaning no real serial was captured, is never used as a
  grouping key, since that would incorrectly collapse every image of one
  *instrument type* into a single group).
- Calibration: temperature scaling (`lens_calibration.fit_temperature`) —
  a single scalar grid-searched to minimize NLL on held-out predictions,
  layered under `evaluation.calibration_report()`'s existing reliability-bin/
  ECE report.
- Error analysis: `error_analysis.analyze_errors()` over held-out
  mispredictions.
- Reproducibility: `TrainingConfig` (seed, epochs, learning rate,
  augmentation policy) + `config_hash()`, `training_execution.git_commit()`.

## 3. Candidate artifact storage

`lens_training_pipeline.export_artifact()` — JSON only (never pickle),
written to `LUMENAI_MODEL_ARTIFACT_DIR` (default `model_artifacts/`),
containing eligible classes, Stage B/C weights, preprocessing version,
calibration parameters, config, config hash, git commit, and the
not-evaluated class list. Checksum: SHA-256 of the serialized JSON,
verified on every load (`live_inference_adapter.load_active_model()`).

## 4. Current model registry

`app.models.model_registry.ModelRegistryEntry` — a real, already-migrated
table (fields: `model_id`, `model_version`, `architecture`, `dataset_version`/
`dataset_version_id`, `git_commit`, `artifact_path`, `artifact_checksum`,
`preprocessing_version`, `training_run_id`, `evaluation_metrics`,
`calibration_report`, `error_analysis_report`, `known_limitations`,
`approval_status`, `clinical_review_status`, `deployment_status`,
`candidate_stage`). `lens_model_registration.register_lens_model()` persists
one training run as one row. `candidate_stage` starts and stays
`"Experimental"` for any run whose `data_provenance` is
`"synthetic_experimental"` (this sprint's own declared experimental run,
per `FIRST_MODEL_SCOPE.md`) — only a run over `data_provenance == "real"`
governed clinical Ground Truth is eligible for `"Candidate"`.

## 5. Preprocessing flow

One shared, versioned contract
(`PREPROCESSING_VERSION = "lens-pillow-features-v1"`,
`lens_training_pipeline.py`) used identically by training
(`run_lens_training()`) and live inference
(`live_inference_adapter.predict()` via `training_execution._feature_vector`)
— brightness/sharpness/aspect-ratio features computed by Pillow, no
numpy/OpenCV/YOLO dependency. Training augmentation
(`augmentation.augment_image_bytes`) is deterministic per `(sample_id,
seed)` and limited to controlled rotation/crop/scale/brightness/contrast/
blur/noise — it never alters residue color, corrosion appearance, or
morphology (enforced by the augmentation module's own transform bounds).

## 6. Image decoding

`training_execution._feature_vector()` and `image_quality.assess_image_bytes()`
both decode via Pillow (`PIL.Image.open`), returning `None`/`decodable:
False` for corrupted or unparseable bytes — never crashing the caller, and
never silently substituting a placeholder value for a feature that
couldn't be computed.

## 7. Current prediction contract (before this sprint)

`live_inference_adapter.predict()` returned (prior to this sprint's Section
16 additions): `analysis_status`, `model{model_id, model_version, status,
preprocessing_version, calibration_version}`, `image_quality{status,
confidence, grade}`, `observation{category, display_label, raw_probability,
calibrated_confidence, abstained, abstention_reason}`,
`supported_categories`, `unsupported_categories`, `baseline_comparison`
(always `null` — populated by the caller, kept separate per Section 17),
`limitations`, `human_review_required`, `inference_timestamp`. Missing
against this sprint's Section 16 spec: a top-level `inspection_id` and an
`image{lcid_image_id, sha256, width, height}` block, and the `model.maturity`
key name (the existing contract used `status` for the same concept). This
sprint adds both, additively (`status` is retained alongside the new
`maturity` key so no existing consumer breaks) — see
`LIVE_INFERENCE_INTEGRATION.md` for the updated contract.

## 8. Production-mode behavior (before this sprint)

There was no explicit "production vs. test/demo" switch anywhere in
`app/config.py` or the inference call chain — `PRODUCTION_INFERENCE_MODE =
"deterministic_placeholder"` in `app.ai.inference` is a *static disclosure
label*, not a runtime gate, and nothing in `analyze_inspection()` refuses to
run the placeholder in any environment. This sprint adds an explicit,
opt-in `settings.ai_strict_no_placeholder` boolean (env var
`AI_STRICT_NO_PLACEHOLDER`, default `False` everywhere, including real
production — `APP_ENV=production` is already set in the real deployment
configs today, so gating on the existing `is_production` property would have
silently changed already-deployed behavior; a separate, deliberately opt-in
flag avoids that). See `LIVE_INFERENCE_INTEGRATION.md` Section "Production
deployment mode" for what setting it to `True` changes
(`_build_model_result()` reports the honest `"unavailable"` state with an
empty findings list instead of a deterministic-placeholder score) and why it
defaults off (no deployment sets it today, so this is zero-risk to every
existing test and disclosed behavior).

## 9. Where placeholder results enter the inspection workflow

`analyze_inspection()`'s placeholder-derived `predicted_findings`/
`kpi_summary`/`model_result` are the values every existing consumer reads:
`app.services.lumen_decision_engine`, `clinical_report_pdf`, the frontend's
`NewInspectionPage` AI Prediction panel, and quality/analytics dashboards.
Project Lens's real `live_model_result` key is **additive only** — nothing
today reads it as the authoritative recommendation; the Decision Engine and
every other consumer are unchanged by its presence
(`test_analyze_inspection_live_model_result_is_additive_only` pins this).
This is intentional and matches the mission's own correct-completion
statement: the candidate is "ready for independent validation and
prospective shadow-mode evaluation," not a production replacement for the
existing (disclosed, false-PASS-remediated) placeholder-scoring path.

## 10. How baseline comparison and model inference remain separate

`baseline_comparison_scoring_service.resolve_baseline()` (metadata-level
baseline lookup) and `image_similarity_service.compare_against_baseline()`
(the real, tested, first-stage perceptual-hash comparator — still not
wired into the live per-inspection path, see
`BASELINE_COMPARATOR_VALIDATION.md`) are entirely separate from
`live_inference_adapter.predict()`. The live adapter's `baseline_comparison`
key is always `null`, populated only by the caller, never computed inside
the adapter itself — so a missing/incompatible/no-approved baseline can
never suppress or alter a probable observation the model reports, and a
high baseline similarity can never cancel a probable-contamination
observation, because the two channels are never merged into one score.
