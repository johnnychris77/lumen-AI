# Live Inference Trace — Project Lens

Full trace of the current image-upload → inference → result path, produced
before any Project Lens code changes, per Section 1's requirement.

## 1. The exact path today

```
Image upload           POST /api/inspections/upload-images (app/routes/inspections.py:900)
  → real sha256        hashlib.sha256(data) over the ACTUAL uploaded bytes (line 937)
  → optional retention  image_retention_service.retain_image() — only when
                        RETAIN_INSPECTION_IMAGES is enabled AND the caller
                        passes consent=true; returns a RetainedImage row
                        with real image_bytes (LargeBinary) when it applies
  → response            {sha256, retained: bool, retained_image_id?, ...}
                        — raw bytes are NEVER returned to the caller

Frontend                NewInspectionPage.tsx:443-496 calls upload-images
                        first, reads imgData.images[0].sha256 (line 463),
                        and threads it into the create-inspection body as
                        image_sha256 (line 496) — confirmed via direct read,
                        this field IS populated from a real upload, not left
                        blank in the normal UI flow

Inference API           POST /api/inspections (app/routes/inspections.py:392)
  → calls                analyze_inspection() from
                        app.services.baseline_comparison_scoring_service
                        (imported line 22, called lines 375 and 438)
  → signature            analyze_inspection(db, *, instrument_type, tenant_id,
                        has_image, image_sha256: str | None, declared_findings,
                        instrument_barcode, instrument_udi, keydot_id,
                        decoder_backend, inspected_zones, training_mode,
                        image_view_tags) — NOTE: takes a sha256 STRING, never
                        image bytes. There is no code path today by which
                        POST /api/inspections can hand real pixels to the
                        scoring function, even when the image was retained.

Preprocessing            NONE. No decode, no resize, no color-space handling
                        happens anywhere in this call chain for the scoring
                        path — the sha256 string is the only "image" input.

Prediction generation    baseline_comparison_scoring_service.py:1059-1479
                        analyze_inspection(): `seed = _seed_from(image_sha256,
                        fallback)` (line 1133) turns the hash into a 32-bit
                        integer; every KPI probability is
                        `_pseudo(seed, idx)` — SHA-256("{seed}:{salt}") interpreted
                        as a float in [0,1). This is a deterministic
                        pseudo-random number generator seeded by a hash of the
                        image bytes, NOT a computer-vision prediction. The
                        module's own docstring (lines 1-3) states this in bold:
                        "THIS IS A DETERMINISTIC PLACEHOLDER — NOT PRODUCTION
                        COMPUTER VISION."

Result mapping            _build_model_result() (lines 133-203) narrows the
                        heuristic's 12 KPIs down to the 2 the deployed model
                        claims to support (SUPPORTED_MODEL_CATEGORIES =
                        ("debris", "corrosion"), app/ai/inference.py:42) —
                        an honest narrowing added in a prior sprint (Core
                        Inspection Workflow Closure), but the underlying
                        finding values it narrows are still placeholder output.

Baseline comparison       resolve_baseline() (lines 487-511) is a REAL
                        database query (BaselineLibraryEntry /
                        EnterpriseVendorBaselineSubscription, manufacturer →
                        vendor → hospital priority) — this part is genuine
                        record resolution, not fabricated. But the numeric
                        "baseline_match_score" (line 1224) is
                        `1.0 - deviation`, where deviation is itself derived
                        from the same seeded-hash pseudo-random value plus a
                        simple count of positive KPI findings (line 1223) —
                        it is NOT a pixel-level comparison between the
                        current image and the approved baseline's image. No
                        baseline image bytes are compared to anything.

Lumen Decision Engine     app/services/lumen_decision_engine.py's
                        build_decision() (wired from
                        POST /api/inspections, per the Decision Engine
                        sprint) consumes whatever analyze_inspection()
                        returns — it correctly treats the model as a
                        black box and applies policy on top, so it is NOT
                        part of the placeholder itself, but everything it
                        reasons about today is placeholder-derived.

Frontend response         NewInspectionPage.tsx renders the model_result /
                        clinical_decision contract, already labeled
                        "Experimental" per the Core Inspection Workflow
                        Closure sprint.
```

## 2. Is a second, dormant real-model code path present?

Yes — `app/ai/inference.py::LumenAIModel` is a **separate, unrelated route
family** (`POST /stream/frame` in `app/routes/inspect.py`, and a queued
variant in `app/routes/stream.py` — confirmed via repo-wide grep: zero
references from any current frontend page). It has real code to load a
YOLO `.pt` file (`_load_model()`, lines 62-80) and run real
`cv2.imdecode()` + `ultralytics` inference (`_predict_with_yolo()`, lines
143-196) on **actual decoded image bytes** — this is genuine, non-fabricated
inference code, dormant only because:

- No `.pt` weights file exists anywhere in this repository or its
  filesystem (confirmed via search).
- `ultralytics`/`cv2`/`numpy` are **not installed** in this environment's
  `.venv` (verified directly: all three raise `ModuleNotFoundError`; only
  `Pillow` is importable). They are declared as optional, `try/except`-guarded
  imports in `inference.py`, never hard dependencies, and `requirements.txt`
  lists only `Pillow==12.3.0`.
- `predict()` (lines 198-205) therefore always falls through to
  `_deterministic_fallback()` — the same seeded-hash pattern as
  `analyze_inspection()`, independently implemented (`MODEL_VERSION`/
  `PRODUCTION_INFERENCE_MODE` constants differ between the two modules —
  they are two separate placeholder implementations, not one shared one).

`app/ai/inference_status.py::get_inference_status()` is the **live,
runtime-checked** answer to "is a real model active" — it reports
`mode: "deterministic_placeholder"`, `yolo_available: False`,
`model_weights_present: False`, `ready_for_production: False` today, and
will keep reporting this honestly no matter what changes elsewhere,
because it checks the filesystem and import machinery at call time rather
than trusting a static flag.

## 3. A real (but toy-scale) training pipeline already exists — and is never loaded back for inference

A prior sprint (Genesis — Production Model Training, Scientific Validation
& Model Governance) built a genuinely real, non-fabricated training
pipeline:

- `app/services/ml/training_execution.py::_feature_vector()` — real,
  Pillow-computed features (brightness mean, Laplacian-style edge-variance
  sharpness, aspect ratio) from actual decoded image bytes.
- `_train_logistic_regression()` — real batch gradient descent, pure Python
  (no numpy/sklearn — this environment has neither installed).
- `app/services/ml/candidate_training.py::run_candidate_training()` /
  `run_full_candidate_pipeline()` — real one-vs-rest multiclass training,
  real leakage-safe split (`dataset_split.split_dataset`), real dataset
  integrity reject-gate, real evaluation/calibration/error-analysis, real
  JSON artifact export (`export_artifact()`, never pickle), real
  `ModelRegistryEntry` registration with a real model card.
- Reachable today via `POST /dataset-registry/versions/{id}/run-candidate-training`
  (`app/routes/dataset_registry.py:438`), which pulls samples from
  `dataset_builder.eligible_entries()` (see Section 5 below for why this
  needs a bridge) and real `RetainedImage.image_bytes`.
- `backend/model_artifacts/genesis-api-model_0.1.0.json` already exists on
  disk — real trained one-vs-rest logistic-regression weights for
  `debris`/`corrosion`/`no_actionable_finding`, produced by a prior test
  run, not hand-written.

**This is genuinely trained, not a fixture or mock** — but nothing anywhere
in the repository ever loads this (or any) artifact back for a live
prediction. `export_artifact()`'s output path is written once and then only
ever read for display/audit purposes (via `ModelRegistryEntry.artifact_path`)
— never for inference. This is the single biggest gap Project Lens closes:
a live inference adapter that actually loads a promoted registry artifact
and uses it to score real uploaded images.

## 4. Where model version is sourced today

Two independent, hardcoded string constants, neither derived from a real
registry lookup at request time:

- `baseline_comparison_scoring_service.MODEL_VERSION =
  "baseline-comparison-placeholder-1.0"`
- `app.ai.inference.LumenAIModel(model_version="0.4.0")` (constructor
  default, `inference.py:51`)

Neither is read from `ModelRegistryEntry` — a real live adapter must source
`model_id`/`model_version` from the actual promoted registry row it loaded,
not a hardcoded literal.

## 5. Dataset eligibility bridge required

`dataset_builder.eligible_entries()` (used by the existing
run-candidate-training route) filters on the **older**
`DatasetRegistryEntry`-level fields: `current_label`, `review_status ==
APPROVED` (sourced from `DoubleBlindReview`, the pre-Annotation-Database
review system), `image_quality != QUALITY_REJECT`, `phi_verification ==
"verified"`, `training_eligibility == True`, plus sha256 dedup.

Project Lens's Section 3 requires eligibility to be anchored on the
**newer, authoritative** Annotation Database's `ground_truth_status ==
"ACTIVE"` (which itself already enforces "primary and independent
secondary review agreement, or completed clinical adjudication" —
`annotation_ground_truth_service.is_eligible_for_ground_truth()`, lines
33-40 — never AI confidence alone). There is no direct FK from `Annotation`
to `DatasetRegistryEntry` — both reference the same `RetainedImage` via
`retained_image_id`. The Project Canvas sprint already built exactly this
join pattern for the Dataset Release Builder
(`dataset_release_service.build_release_preview()`); Project Lens's new
`training_eligibility_service` (Section 4/Task #436) reuses the identical
join, replacing `dataset_builder.eligible_entries()`'s stale
`DoubleBlindReview`-based filter for training-sample selection specifically
(the older path is left untouched for anything else still using it).

## 6. Dataset split — grouping key gap

`app/services/ml/dataset_split.py::split_dataset()`/`has_no_group_leakage()`
are real, reusable, pure-Python, generic dict-based functions — no change
needed to the splitter itself. But
`dataset_builder._sample_dict()` hardcodes `"instrument_serial": None`, so
today's split groups only by `inspection_id`, never by the stronger
`digital_twin_id` identity that already exists as a real column on both
`DatasetRegistryEntry` and `Annotation`. Project Lens's new eligibility/
sample-building path populates `instrument_serial` from `digital_twin_id`
and calls `split_dataset(..., group_by_serial=True)` so images of the same
physical instrument across different inspections never straddle a split
boundary — reusing the splitter exactly as built, only supplying it a
better grouping key.

## 7. Baseline comparison — no real image comparison exists anywhere

Confirmed via repo-wide grep (`structural_similarity|phash|imagehash|
cosine|embedding|ssim`): **zero results**. No perceptual hash, no
embedding, no SSIM, no pixel-level comparison of any kind exists in this
codebase today. `app/services/baseline_comparison_service.py` (built in
the Project Canvas sprint) resolves WHICH baseline record(s) are
available — real record resolution — but computes no similarity score at
all. All "similarity"/"match" numbers shown anywhere today
(`baseline_match_score` in the inspection-scoring path) come from the same
seeded-hash arithmetic as everything else. Section 18's honest
feature-based comparator is entirely new work — see
`BASELINE_COMPARATOR_VALIDATION.md`.

## 8. Shadow / Advisor — prediction-source-agnostic, confirmed real infra

`shadow_mode.record_shadow_prediction()` and the Advisory-Mode routes
operate on whatever `predicted_label`/`predicted_confidence` the caller
supplies (`app/routes/model_pipeline.py::create_shadow_prediction()` takes
these directly from the request body) — they do not themselves invoke any
model. This means Shadow/Advisor infrastructure will work unchanged the
moment a real adapter's predictions are fed into it; no changes are needed
there for Project Lens's scope (wiring the live adapter into
`POST /api/inspections`, not into the separate shadow-recording endpoint).

## 9. Dependencies — pure Python + Pillow only

`requirements.txt` (both the root and `app/` copies) declare only
`Pillow`. No numpy, scikit-learn, torch, tensorflow, onnxruntime, or
opencv. Directly verified in this environment's `.venv`
(`/home/user/lumen-AI/.venv`, Python 3.11): every one of those imports
raises `ModuleNotFoundError` except `PIL`. `ultralytics`/`cv2`/`numpy` are
referenced in `app/ai/inference.py` behind `try/except ImportError` guards
only. This directly informs the architecture decision in
`MODEL_ARCHITECTURE_DECISION.md` — a CNN/transfer-learning backbone is not
executable in this environment today, and would not be appropriate for the
dataset sizes realistically available (see `TRAINING_ELIGIBILITY_REPORT.md`)
even if it were.

## 10. Existing test image fixtures

No static image files exist under `backend/tests/`. Every test that needs
an image builds one inline via `PIL.Image.new(...)` (e.g.
`tests/test_candidate_model_training.py::_img()` — 300×300 RGB with a
striped brightness pattern, real PNG-encoded bytes). Project Lens's
live-path tests (`Task #443`) follow this same established convention
rather than introducing a new fixture mechanism.

## 11. What must change to use a trained artifact safely

1. A training-eligibility service anchored on Annotation-level ACTIVE
   Ground Truth (Section 5 above), not the older DoubleBlindReview path.
2. A leakage-safe split grouped by `digital_twin_id` (Section 6).
3. A live inference adapter that (a) loads the highest-`candidate_stage`
   real, checksummed `ModelRegistryEntry` artifact for the deployed model
   family, (b) decodes real image bytes when they are available (only when
   `RETAIN_INSPECTION_IMAGES` + consent produced a `RetainedImage` row —
   otherwise there ARE no server-side pixels to evaluate, a genuine,
   disclosed data-availability constraint distinct from "no model
   available"), (c) applies the same `_feature_vector()`/preprocessing
   contract used at training time, (d) applies calibration + abstention
   thresholds, (e) returns the Section 19 result contract.
4. `analyze_inspection()` must be extended **additively** — exactly the
   same pattern the Core Inspection Workflow Closure sprint already used
   for `_build_model_result()` — so that when a real, eligible artifact is
   registered and real image bytes exist for this submission, the adapter's
   real prediction populates the model-facing fields, while the existing
   KPI heuristic (which the Decision Engine, reports, and dashboards still
   read) is left completely unchanged for backward compatibility. This
   means: by default, with no promoted artifact registered (today's state,
   and every existing test's state), behavior is byte-for-byte identical
   to today — the deterministic placeholder remains the disclosed,
   intentionally-still-active mode for this pre-pilot deployment (which
   KNOWN_LIMITATIONS.md already discloses has never served real customer
   traffic). The moment a real artifact is trained on real eligible data
   and promoted, its predictions are used instead, automatically, without
   any other code change.
5. A feature-based baseline comparator (Section 7 above) — new, does not
   yet exist in any form.
6. Safe unavailable-model states (Section 16 of the spec) distinct from,
   and in addition to, the existing "no approved baseline" gate that
   `analyze_inspection()` already enforces.
