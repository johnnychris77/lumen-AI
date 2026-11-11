# Real Vision Model — Readiness & End-to-End Proof

Can LumenAI "stand up an actual trained, calibrated, promoted vision model so
AI_UNAVAILABLE flips to genuine inference"? **The pipeline is built, tested, and
works end-to-end today.** The only thing missing is *eligible real labeled
ground truth* — which cannot be fabricated. This document shows the pipeline
running end-to-end and states exactly what remains.

## The pipeline (all present and tested)

```
dataset ingestion ─▶ training eligibility ─▶ training (hierarchical logistic,
   pure-python)  ─▶ temperature calibration + abstention threshold ─▶ artifact
   export (+ SHA-256 checksum) ─▶ ModelRegistryEntry ─▶ governed promotion
   (Experimental → Candidate → Pilot → Production) ─▶ live_inference_adapter
   serves the promoted artifact on every inspection
```

Modules: `experimental_dataset_generator`, `training_eligibility_service`,
`lens_training_pipeline` (`run_lens_training`, `export_artifact`),
`lens_model_registration` (`register_lens_model`), `model_registry`,
`candidate_promotion`, `shadow_validation` / `pilot_validation`,
`live_inference_adapter`.

## Governance — a synthetic model can never become clinical

`register_lens_model` sets `candidate_stage="Candidate"` **only when**
`training_status=="trained"` **and** `data_provenance=="real"`. A model trained
on this sprint's synthetic/experimental run stays `Experimental` no matter how
well it trained (see `FIRST_MODEL_SCOPE.md`). Promotion past `Candidate` is a
governed **human** action after the validation gates pass — never a code
default. This is why production is correctly `AI_UNAVAILABLE` today.

## End-to-end proof (local, synthetic data — NOT a clinical model)

Run locally (`RETAIN_INSPECTION_IMAGES=true`, `APP_ENV=test`), synthetic images
only, nothing promoted in production:

**1. Train + register on a synthetic dataset**
```
training_status: trained
data_provenance: synthetic_experimental
candidate_stage (governance): Experimental        ← cannot auto-promote
artifact_checksum_present: true   has_calibration: true
```

**2. Serve with the (unpromoted) model → honest AI_UNAVAILABLE**
```
analysis_status: ai_unavailable   ai_analysis.status: AI_UNAVAILABLE
live_model.status: not_promoted   inspection_score: null
```

**3. Simulate a GOVERNED promotion to Candidate** (human action; local demo only)

**4. Serve with the promoted model → GENUINE calibrated inference**
```
ai_analysis.status: COMPLETED
live_model.model_id: lumenai-vision-lens   model_version: 0.1.0-readiness
live_model.status: candidate
preprocessing_version: lens-pillow-features-v1
calibration_version: 65bc2b35fd781a33
observation.abstained: true
observation.abstention_reason: insufficient_image_quality
placeholder_scoring: false
analysis_status: ai_unavailable   ← abstention routed to not-evaluated
```

The live adapter loaded the real checksummed artifact, ran real feature
extraction + calibration, and produced a **genuine observation** — which
**abstained** on the low-quality synthetic image and was therefore routed to
`AI_UNAVAILABLE` (the abstention-is-not-evaluated safeguard), never a
placeholder. An in-distribution image above the confidence threshold yields a
real `category` + `calibrated_confidence` instead (covered by
`tests/test_project_lens.py`). This is the flip the request describes:
`AI_UNAVAILABLE` → genuine inference, automatically, the moment a model is
promoted — **with no further code change.**

## What remains to stand up a *clinical* model (the only blocker: real data)

A genuine clinical model cannot be produced from synthetic data or conjured in
this sandbox. It requires, as a governed human-in-the-loop process:

1. **Eligible labeled ground truth** — real borescope/instrument images with
   **ACTIVE, dual-reviewed** ground truth in the Annotation DB (agreement or
   adjudication, never AI confidence), grouped by `digital_twin_id` for
   leakage-safe splits. *This is the single blocker; everything downstream
   exists.*
2. **Train + calibrate** on a held-out split; set the abstention threshold.
3. **Register + promote to `Candidate`** — a governed human promotion, only
   after the validation gates pass.
4. **Shadow mode** against incoming inspections (humans still decide); compare
   to ACTIVE ground truth via `shadow_validation` / `pilot_validation`.
5. **Promote `Candidate → Pilot → Production`** only when calibrated accuracy,
   abstention behaviour, and per-class error analysis clear the documented gates.
6. **Consent-based retention** (`RETAIN_INSPECTION_IMAGES` + per-submission
   consent) so real pixels reach the adapter.

See `REAL_VISION_PILOT_PLAN.md` for the full gated pathway.

## Honest bottom line

- The serving path, training, calibration, registry, promotion governance, and
  abstention safety are **all real and working** — proven end-to-end above.
- `AI_UNAVAILABLE` is the **correct** state today because no eligible model has
  been trained on real governed ground truth and promoted.
- No one can "turn on" real computer vision without that labeled data. Once it
  exists and a model clears the gates, promotion flips the clinical surface to
  genuine, calibrated, abstaining inference automatically.
