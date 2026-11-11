# Make Real Manufacturer Baseline Image Comparison Operational

Inspection #15 uploaded a photograph but reported *"No visual (pixel) comparison
was performed."* This change makes the comparison actually run, end-to-end.

## Task 1 — Exact cause of Inspection #15's failed comparison

**The inspection's pixel bytes never reached the comparator, because pixel
availability was coupled to opt-in *training* retention.**

The comparator (`_live_baseline_comparison`) needs the inspection image bytes.
The create-inspection route only obtained those bytes from a `RetainedImage`
row, which `image_retention_service.retain_image()` creates **only when**
`RETAIN_INSPECTION_IMAGES` is enabled **and** per-submission consent is given.
In the pilot deployment that long-term training retention is off, so:

```
retained_image_bytes = None
  → analyze_inspection(image_bytes=None)
  → compare_against_baseline(image_bytes=None, baseline_image_bytes=…)
  → status = insufficient_quality / no numeric comparison
  → "No visual (pixel) comparison was performed."
```

This is **not** caused by the absence of a trained AI model — the baseline-image
comparison is a separate, deterministic perceptual comparator that does not need
a trained model. It only needed the pixels.

A second thing to confirm from the live record (both are required for a real
comparison) is whether the manufacturer reference image is actually **ACTIVE**.
To triage any inspection, retrieve (tenant-scoped, read-only):
`analysis.baseline_evidence`, `analysis.ai_analysis.baseline_image_similarity`,
`analysis.live_model_result.baseline_comparison`, the resolved baseline record id,
the `BaselineImageLink` id + `lifecycle_status`, its `lcid_image_id` and
`retained_image_id`, the inspection's tenant / manufacturer / model / anatomy
zone / inspection view, and the comparison `status` + `resolution_reason`. If the
baseline was created by the **legacy hash-only** path its bytes were never
retained and it must be re-registered through the governed workflow (upload →
review/approve → activate) — see `MANUFACTURER_BASELINE_IMAGE_INTEGRATION.md`.

## Task 3 — Separate processing from training retention

New **temporary processing pathway**, independent of training retention:

- `app/models/inspection_processing_image.py` — a bounded, tenant-scoped,
  EXIF-stripped store for the pixels needed to run the comparison the user
  requested. Carries `expires_at`; nothing in the training/dataset pipeline
  reads it.
- `app/services/inspection_image_processing_service.py` — `store` (on upload),
  `load_processing_bytes` (tenant-scoped + hash-verified), `consume` (nulls the
  bytes once used), `purge_expired`.
- `/api/inspections/upload-images` now stores a processing copy in addition to
  the hash (and the optional, consent-gated training copy).
- `/api/inspections` prefers the processing bytes for analysis, then **consumes**
  them (bytes removed). No training-data retention happens without the separate
  `RETAIN_INSPECTION_IMAGES` + consent.

Guarantees: EXIF-stripped; strict tenant scope on every read; hash-verified on
load; bytes nulled on consume; expired rows purged; never enrolled in training.

## Task 4 — Comparison made functional (and its honest limits)

With an ACTIVE, compatible reference, the flow now retrieves the real reference
bytes (hash-verified) and the real inspection bytes (hash-verified, tenant
scoped), validates manufacturer/model/anatomy/view/tenant compatibility, decodes
both, checks image quality, and runs the existing genuine comparator
(`image_similarity_service`, average-hash Hamming, `lens-average-hash-v1`),
recording method, version, baseline-image id, status, similarity and
limitations. A numeric similarity is returned **only** when a real comparison
succeeded; no hash-seeded or placeholder value is ever substituted.

**Assessment (pilot):** the comparator is a coarse **perceptual-hash similarity**
after scale normalization (the average-hash resizes to a canonical grid). It is
labelled *"Visual similarity — not verified cleanliness"* everywhere and is
**not** defect detection. Robuster image alignment / registration, view-pose
normalization and learned features are future work and are called out as such —
this change does not present perceptual similarity as validated defect detection
or a cleanliness score.

## Task 5 — Separate, non-overstated results

`baseline_evidence` exposes seven independent facts, and the manufacturer
reference comparison (link id, version, status, visual similarity, method,
limitations) is rendered — on the New Inspection page, in the raw API response,
in `/api/history` (`baseline_image_comparison`), and in the clinical report —
separately from the trained-model status (available/unavailable, supported
categories, calibrated confidence, human-review requirement). Visual similarity
is never turned into a cleanliness score, contamination diagnosis, or release
authorization.

## Task 2/6 — End-to-end evidence (local, real HTTP + governed baseline)

Upload a photo → inspect it against its ACTIVE manufacturer reference:

```
UPLOAD:            processing_available: true

RAW API (manufacturer baseline comparison):
  baseline_image_link_id: 1      reference_version: 1.0
  comparison_status: materially_different   visual_similarity: 0.4375
  method: average_hash_hamming   comparator_version: lens-average-hash-v1
  is_image_comparison: true      label: "Visual similarity — not verified cleanliness."

SEPARATION (baseline evidence vs trained model):
  metadata_found✓ image_registered✓ image_active✓ image_compatible✓
  inspection_image_bytes_available✓ real_image_comparison_completed✓
  trained_vision_model_available: false

CLINICAL SAFETY:
  ai_analysis.status: AI_UNAVAILABLE   predicted_findings: []   inspection_score: null
  authorizes_release: false            human_review_required: true

PERSISTENCE + PROCESSING LIFECYCLE:
  persisted_similarity: 0.4375   persisted_link_id: 1   persisted_method: average_hash_hamming
  processing_status: consumed    processing_bytes_present: false
  enrolled_in_training_dataset: false   enrolled_in_training_retention: false

CLINICAL REPORT: HTTP 200, valid PDF (comparison section rendered)
```

The two photos were deliberately different (0.4375 similarity) — the comparator
responds to actual image differences, not a fixed value. A different pair yields
a different similarity; an identical pair yields `exact_match`.

`backend/tests/test_baseline_image_comparison_operational.py` (10 tests) covers
the happy path, difference sensitivity, incompatible manufacturer, missing
inspection bytes, cross-tenant denial, hash-mismatch rejection, no-training
enrolment, expiry purge, and the report rendering. Full backend suite **3822
passed, 2 skipped**; ruff + frontend build clean.

## Production verification (honest limitation)

This CI/sandbox cannot reach `*.onrender.com` (proxy 403), so the live services
were not driven and Inspection #15's live record was not read from here. The
cause above is established from the code path and reproduced locally; the live
fix is this deployment change plus (if #15's baseline was legacy hash-only)
re-registering its reference image through the governed workflow. After deploy,
re-run an inspection of that instrument: the New Inspection page will show
"Baseline reference image: compared — visual similarity N%" and the API/report
will carry the same result, while the trained-model status stays AI_UNAVAILABLE.
