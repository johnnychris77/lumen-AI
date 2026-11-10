# Real Vision Pilot — Integration Plan (Phase 2)

The smallest secure pathway from today's disclosed deterministic-placeholder
deployment to genuine, governed visual analysis of real instrument photographs.
This plan does **not** promote any model to make the UI display AI results, and
does **not** use SHA‑256‑seeded findings, random scores, or fixed simulated
observations as real inference. It builds on the honest infrastructure that
already exists (`live_inference_adapter`, `image_similarity_service`,
`training_execution`, `ModelRegistryEntry`, the Annotation ground‑truth DB).

## Current state (from the trace)

- `live_inference_adapter.predict` already loads a **real** checksummed, promoted
  (`≥ Candidate`) `ModelRegistryEntry` artifact, decodes real retained image
  bytes, runs real feature extraction + hierarchical logistic weights +
  calibration + abstention, and returns the result contract — otherwise an
  honest `AI_UNAVAILABLE` state. Today every model is `Experimental`, so this is
  always `AI_UNAVAILABLE` (correct).
- `image_similarity_service` is a real aHash/Hamming comparator; the baseline
  channel verifies stored baseline bytes' hash on access before comparing.
- `analyze_inspection` now surfaces an **authoritative** `ai_analysis` block
  derived only from the live contract; the placeholder findings/score are
  explicitly labelled `verified_ai: False` / `provenance: deterministic_placeholder`.

What's missing is **not** the serving path — it's eligible ground truth, a
trained-and-promoted model, and the pilot measurement loop.

## The minimal secure pathway

### 1. Image decoding & image‑quality assessment
- Already present: `ml/image_quality.assess_image_bytes` (decodable, dimensions,
  brightness/sharpness grade) and the adapter's reject/poor gate.
- **Needed:** nothing new to decode; confirm quality thresholds against the first
  real labelled set and record the chosen thresholds in the model card.

### 2. Instrument identity & manufacturer/model compatibility
- Already present: identifier decode (pyzbar) + `identifier_match` against the
  approved baseline UDI; `baseline_compatibility_service.check_compatibility`
  gates the baseline‑image channel by instrument family / manufacturer.
- **Needed:** require a `COMPATIBLE` baseline resolution before any similarity is
  surfaced (already enforced); add compatibility to the model's own input
  guard so an out‑of‑family image abstains rather than scores.

### 3. Approved manufacturer baseline‑image retrieval
- Already present: `resolve_baseline_image` (5‑level hierarchy) +
  `load_and_verify_baseline_bytes` (ACTIVE link, hash‑verified bytes).
- **Needed:** operational step — manufacturers/vendors must upload real baseline
  images that pass governance (Submit → Verify → Approve → Publish) so ACTIVE
  linked bytes exist; without them the comparator correctly returns
  `no_approved_baseline` / `insufficient_quality`.

### 4. Real vision‑model inference
- Already present: real training (`training_execution`, `candidate_training`),
  JSON artifact export, registry registration, and the serving adapter.
- **Needed (the gating work):**
  1. Assemble eligible training data anchored on Annotation‑DB
     `ground_truth_status == "ACTIVE"` (dual‑review agreement or adjudication —
     never AI confidence), grouped by `digital_twin_id` for leakage‑safe splits.
  2. Train, calibrate (temperature), and set an abstention threshold on a
     held‑out set.
  3. Register the artifact and **promote to `Candidate`** only after the
     validation gates below pass. Promotion is a governed human action, not a
     code default.

### 5. Supported vs unsupported finding categories
- The artifact's `eligible_classes` / `not_evaluated_classes` drive
  `supported_categories` / `unsupported_categories`. Unsupported categories are
  returned as names only — never with a confidence. Keep the deployed scope
  small (today: `debris`, `corrosion`) and widen only as labelled data supports
  each new class.

### 6. Observation provenance, model version, calibrated confidence
- The contract already carries `model_id`, `model_version`,
  `preprocessing_version`, `calibration_version`, `raw_probability`,
  `calibrated_confidence`, `abstained`, `abstention_reason`. `ai_analysis`
  re‑exposes these as the authoritative AI observation. No hardcoded version
  strings on the live path.

### 7. Abstention when evidence / image quality is insufficient
- Already enforced: reject/poor image quality → abstain; confidence below
  threshold → abstain; unknown class → abstain; no bytes → `AI_UNAVAILABLE`.
  Abstention always sets `human_review_required: True`.

### 8. Independent contamination & instrument‑integrity risk
- Keep contamination (cleaning) and integrity (structural) as **separate**
  channels so a high baseline similarity can never cancel a probable
  contamination, and vice‑versa. The baseline comparator is advisory only and is
  never read back into the observation (already true in `_live_model_result`).

### 9. Supervisor validation & audit logging
- Route unavailable/abstained/any‑positive results into the existing supervisor
  review workflow; every inference and every disposition writes an audit event
  (hash‑chained enterprise audit). No model result authorizes release
  (`authorizes_release: False`, enforced + tested).

### 10. Pilot performance measurement vs expert ground truth
- Run the model in **shadow mode** (`shadow_mode.record_shadow_prediction`)
  against incoming inspections while humans decide, and compare predictions to
  Annotation‑DB ACTIVE ground truth via the existing
  `shadow_validation_metrics` / `pilot_validation` services.
- Promote past `Candidate` → `Pilot` → `Production` only when calibrated
  accuracy, abstention behaviour, and per‑class error analysis clear the
  documented gates on a held‑out expert‑labelled set.

## What remains to begin testing real instrument photographs

1. **Eligible labelled data** — real borescope/instrument images with ACTIVE
   dual‑reviewed ground truth (the single blocker; everything downstream exists).
2. **Published ACTIVE baseline images** with verified bytes per instrument family
   (for the similarity channel).
3. **A trained, calibrated, promoted artifact** (`≥ Candidate`) registered for
   the deployed `model_id` — a governed human promotion after the gates pass.
4. **Consent‑based retention enabled** so real pixels reach the adapter
   (`RETAIN_INSPECTION_IMAGES` + per‑submission consent). Without it the adapter
   correctly reports no server‑side pixels to evaluate.

Once (1)–(4) exist, the serving path already in place uses the real model
automatically, with no further code change — and `ai_analysis` flips from
`AI_UNAVAILABLE` to a real, calibrated, abstaining observation.
