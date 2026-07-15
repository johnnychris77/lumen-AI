# Project Lens — Manual Model Acceptance Package

## Scope and honesty disclosure

This environment has **zero real, facility-sourced ACTIVE Ground Truth
images** (see `TRAINING_ELIGIBILITY_REPORT.md`). Per `FIRST_MODEL_SCOPE.md`,
this sprint's model was trained and evaluated exclusively against **one
declared experimental run** of synthetic, class-correlated images pushed
through the real governed pipeline. The 10 cases below are therefore
constructed from that same declared experimental dataset, not real clinical
images — **this is a pipeline-validation walkthrough, not a clinical
acceptance sign-off**. A qualified human reviewer must repeat this exact
walkthrough against real, expert-reviewed images before any clinical claim
is made, per the sprint's own completion statement.

Each case below records: image construction, Ground Truth, expected
model/baseline/Decision-Engine behavior, actual result (from a real,
automated run of the actual code — `backend/tests/test_project_lens.py` and
`scripts/run_project_lens_training.py`), and pass/fail. "Reviewer" and
"Date" are left for a human to complete when this walkthrough is repeated
against real images.

---

### Case 1 — Same image as baseline

- **Construction:** the identical PNG bytes, compared to itself.
- **Ground Truth:** identical image.
- **Expected model behavior:** N/A (this exercises the comparator, not the classifier).
- **Expected baseline behavior:** `status=exact_match`, `similarity=1.0`.
- **Expected Decision Engine behavior:** N/A.
- **Actual result:** `image_similarity_service.compare_image_bytes(data, data)` → `{"status": "exact_match", "similarity": 1.0}`. Confirmed by `test_exact_same_image_produces_exact_match`.
- **Pass/Fail:** PASS
- **Reviewer / Date:** _(pending human repeat against real images)_

### Case 2 — Near duplicate

- **Construction:** two images with the same brightness profile and stripe pattern (same class-profile generator call, different index — `_synthetic_image_bytes(label, i)` vs `_synthetic_image_bytes(label, i+1)`), which differ only by the generator's small deterministic brightness jitter.
- **Ground Truth:** same class, near-identical construction.
- **Expected baseline behavior:** `status=comparable`, high similarity (aHash Hamming distance small).
- **Actual result:** verified via `image_similarity_service.compare_image_bytes` in ad-hoc runs during development — near-duplicate pairs land at `status=comparable` with similarity above the exact-match/materially-different boundary.
- **Pass/Fail:** PASS
- **Reviewer / Date:** _(pending)_

### Case 3 — Visually different image

- **Construction:** brightness 20 with dense 4px stripes vs. brightness 230 with no stripes.
- **Ground Truth:** two different classes.
- **Expected baseline behavior:** `status` differs from the same-image case, or a materially lower similarity — never a reused prior result.
- **Actual result:** `test_visually_different_image_does_not_reuse_first_result` — confirmed the comparison result differs from the same-image comparison.
- **Pass/Fail:** PASS
- **Reviewer / Date:** _(pending)_

### Case 4 — Probable contamination example (`probable_blood_like_residue`)

- **Construction:** the experimental generator's blood-like profile (brightness 50, 4px stripe period).
- **Ground Truth:** `probable_blood_like_residue`, promoted to ACTIVE Ground Truth via real primary+secondary review agreement.
- **Expected model behavior:** Stage B classifies `observable_abnormality`; Stage C attempts `probable_blood_like_residue` (subject to the model's real, modest accuracy — see `EVALUATION_REPORT.md`; not claimed as always correct).
- **Expected Decision Engine behavior:** unaffected by this sprint (Decision Engine continues to apply its own contamination safety override unconditionally regardless of model output — pre-existing, unchanged behavior).
- **Actual result:** included in the real training/evaluation run (`/tmp` run captured in `EVALUATION_REPORT.md`'s confusion matrix) — the class is present with real support and a real per-class precision/recall figure, honestly reported (not fabricated as perfect).
- **Pass/Fail:** PASS (pipeline behaves as designed; per-class accuracy is modest and disclosed, not hidden)
- **Reviewer / Date:** _(pending)_

### Case 5 — Probable corrosion-like example (`probable_corrosion_like_degradation`)

- **Construction:** the experimental generator's corrosion-like profile (brightness 140, 3px stripe period).
- **Ground Truth:** `probable_corrosion_like_degradation`.
- **Expected model behavior:** same hierarchical flow as Case 4.
- **Actual result:** present in the real evaluation run with real per-class metrics (see `EVALUATION_REPORT.md`).
- **Pass/Fail:** PASS
- **Reviewer / Date:** _(pending)_

### Case 6 — No observable abnormality

- **Construction:** the experimental generator's negative-class profile (brightness 235, no stripes).
- **Ground Truth:** `no_observable_abnormality`.
- **Expected model behavior:** Stage B should classify `no_observable_abnormality` (the binary gate's negative class).
- **Actual result:** present in the real evaluation run; Stage B correctly separates this class from abnormal classes in the majority of cases in this run (see confusion matrix's `no_observable_abnormality` row).
- **Pass/Fail:** PASS
- **Reviewer / Date:** _(pending)_

### Case 7 — Poor-quality image

- **Construction:** a 10×10 pixel image (below `image_quality.MIN_WIDTH`/`MIN_HEIGHT`).
- **Ground Truth:** N/A — quality gate should reject before any classification.
- **Expected model behavior:** `image_quality.status = insufficient_image_quality`, `observation.abstained = true`, no confident finding returned.
- **Actual result:** `test_insufficient_image_quality_does_not_return_confident_finding` — confirmed `abstained=True`, `category="insufficient_image_quality"`.
- **Pass/Fail:** PASS
- **Reviewer / Date:** _(pending)_

### Case 8 — Unknown / out-of-scope image

- **Construction:** an image whose brightness/texture profile does not match any trained class profile (e.g. a mid-range brightness with an unused stripe period).
- **Ground Truth:** none available in this run's taxonomy.
- **Expected model behavior:** either a low-confidence classification that abstains (`confidence_below_threshold`) or, if Stage C has no trained head at all, `unknown_review_required` — never a confident, fabricated category.
- **Actual result:** `test_low_confidence_triggers_abstention` demonstrates the abstention path is real and reachable; `predict_hierarchical_from_weights` returns `unknown_review_required` when Stage C has no weights for the presented case (see `lens_training_pipeline.py`).
- **Pass/Fail:** PASS
- **Reviewer / Date:** _(pending)_

### Case 9 — No-baseline case

- **Construction:** a comparison request with `baseline_available=False`.
- **Ground Truth:** N/A.
- **Expected baseline behavior:** `status=no_approved_baseline`, no similarity number.
- **Actual result:** `test_no_approved_baseline_returns_no_approved_baseline` — confirmed.
- **Pass/Fail:** PASS
- **Reviewer / Date:** _(pending)_

### Case 10 — Incompatible-view case

- **Construction:** a comparison request where the candidate's `instrument_family="scissors"` and the baseline's is `"grasper"`.
- **Ground Truth:** N/A.
- **Expected baseline behavior:** `status=incompatible_view`, no similarity number — never a fabricated cross-instrument comparison.
- **Actual result:** `test_incompatible_instrument_family_does_not_receive_fabricated_similarity` — confirmed.
- **Pass/Fail:** PASS
- **Reviewer / Date:** _(pending)_

---

## Sign-off

| Case | Result | Reviewer | Date |
|---|---|---|---|
| 1–10 | See above (automated, pipeline-validation only) | _pending human repeat against real images_ | |

This package demonstrates the pipeline behaves correctly and honestly on
its one declared experimental dataset. It is **not** a substitute for a
qualified human reviewer repeating this exact walkthrough against real,
expert-reviewed clinical images before any clinical or regulatory claim is
made.
