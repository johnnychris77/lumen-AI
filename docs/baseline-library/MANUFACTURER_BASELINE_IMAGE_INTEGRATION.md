# Manufacturer Baseline Image Registration + Real Inspection Comparison

Fixes two defects that made an "approved" manufacturer baseline image unusable by
the inspection comparison engine, while keeping reference-image comparison
strictly separate from trained-AI defect detection.

## The two defects

1. **Registration stored only a hash.** `CreateManufacturerBaseline.tsx` called
   `/api/baselines/upload-images`, which recorded a SHA-256 but never retained
   the bytes or created a governed `BaselineImageLink`. An approved baseline had
   metadata but no usable reference image.
2. **Resolution could never match a manufacturer image.**
   `_live_baseline_comparison()` built `CandidateContext` from only `tenant_id` +
   `instrument_family`. With no manufacturer/model/anatomy/view, the resolution
   hierarchy's manufacturer-specific levels (1–3) could never match, so a
   manufacturer reference image was never compared.

## What changed

### Task 1 — genuine, governed registration (no duplicate storage)
- New `image_retention_service.retain_reference_image()` — persists reference
  bytes in the existing `RetainedImage` store (EXIF-stripped, dedup-aware),
  governed by an explicit **usage-rights attestation** rather than the
  inspection-training `RETAIN_INSPECTION_IMAGES` flag.
- New `baseline_image_registration_service.register_manufacturer_reference_image()`
  orchestrates the existing infrastructure end-to-end:
  `retain_reference_image` → `dataset_registry.register_image` (LCID
  `DatasetRegistryEntry`) → `link_lcid_image_to_baseline` (DRAFT) →
  `submit_for_review` (PENDING_REVIEW).
- New route `POST /api/baselines/{entry_id}/reference-image` (admin/spd_manager),
  wired into the Manufacturer Baseline form.
- **An image is never ACTIVE just because the metadata baseline was approved.**
  Activation stays a governed human decision (review → activate) through the
  existing Baseline Image Library endpoints and its activation gate. A legacy
  hash-only baseline (bytes unavailable) must be **re-uploaded** and governed —
  bytes are never fabricated or reconstructed.

### Task 2 — correct resolution
- `analyze_inspection` now builds a candidate identity (manufacturer + model from
  the resolved approved baseline record, anatomy zone / inspection view from the
  inspection's image tags / inspected zones, Digital Twin id from the
  instrument identifiers) and threads it into `_live_baseline_comparison` →
  `CandidateContext`.
- Zone/view default to the same `whole_instrument` / `overview` tokens the
  reference-image registration uses when neither side scopes them — an explicit
  match on equal documented fields. The existing compatibility contract still
  rejects different manufacturers, models, anatomy zones, views, or tenants.

### Task 3 — baseline evidence separated from AI inference
`analyze_inspection` exposes `baseline_evidence` with **seven independent facts**:
`manufacturer_baseline_metadata_found`, `baseline_image_registered`,
`baseline_image_active`, `baseline_image_compatible`,
`inspection_image_bytes_available`, `real_image_comparison_completed`,
`trained_vision_model_available`. A numeric visual similarity appears only after
verified bytes are compared by the real comparator, and is always labelled
"Visual similarity — not verified cleanliness" — never contamination detection,
verified cleanliness, or release permission.

### Task 4 — honest frontend messaging
The New Inspection AI-unavailable view renders the seven facts as explicit
yes/no chips plus a plain-language reference-image status (registered / awaiting
approval / incompatible / inspection bytes unavailable / comparison available).
The "AI will generate a risk score automatically" copy was removed.

## End-to-end evidence (LOCAL — governed pipeline)

A real instrument photograph compared against verified ACTIVE manufacturer
baseline-image bytes, produced by driving the governed flow
(`register → review(approve) → activate → inspect`):

```
RAW COMPARISON:
  comparison_status: exact_match
  matched_baseline_image_link_id: 1
  similarity: 1.0
  method: sha256_exact          comparator_version: lens-average-hash-v1
  is_image_comparison: true     label: "Visual similarity — not verified cleanliness."

SEVEN PROVENANCE FACTS:
  manufacturer_baseline_metadata_found: true
  baseline_image_registered: true
  baseline_image_active: true
  baseline_image_compatible: true
  inspection_image_bytes_available: true
  real_image_comparison_completed: true
  trained_vision_model_available: false     ← trained model correctly unavailable

REDACTED ANALYSIS RESPONSE:
  ai_analysis.status: AI_UNAVAILABLE   analysis_status: ai_unavailable
  predicted_findings: []               inspection_score: null
  authorizes_release: false            human_review_required: true
  baseline_source: manufacturer
```

A genuine baseline-image comparison completes **while the trained vision model
remains AI_UNAVAILABLE** — the two are independent, and no finding, score, or
clinical clearance is fabricated. (`method` is `sha256_exact` only because the
evidence run reuses identical bytes; a distinct inspection photo yields an
`average_hash_hamming` similarity < 1.0.)

## Tests
`backend/tests/test_manufacturer_baseline_image_integration.py` — 11 regression
tests covering: metadata baseline without a usable image; hash-only uploads are
not image-backed; a retained/registered/approved/ACTIVE image resolves;
manufacturer/model/anatomy/view compatibility enforced; cross-tenant isolation;
inactive/rejected images unusable; hash-integrity failure blocks comparison;
compatible bytes produce a traceable similarity; no inspection bytes →
unavailable comparison; no trained model still yields AI_UNAVAILABLE even when a
real comparison succeeds; no fabricated finding or clearance.

Full backend suite: **3812 passed, 2 skipped**; `ruff` clean; frontend `vite
build` clean.

## Production verification (honest limitation)
This CI/sandbox cannot reach `*.onrender.com` (outbound proxy returns 403), so
the live services were not driven from here. The baseline created before
Inspection #14 was stored under the **legacy hash-only** path — its actual bytes
were never retained, so it cannot be reconstructed. To make it usable in
production, re-register its source image through the governed workflow:

1. Open the Manufacturer Baseline form and create/confirm the baseline record,
   then upload the reference image with source organization + reference and the
   usage-rights / no-PHI attestations (this calls
   `POST /api/baselines/{id}/reference-image`).
2. In the Baseline Image Library, **review → approve** the PENDING_REVIEW link,
   then **activate** it (the activation gate verifies retained bytes, rights,
   PHI, quality, review, and hash).
3. Run a new inspection of that instrument; the New Inspection page will then
   show a real "Baseline reference image: compared — visual similarity N%" line
   and `real_image_comparison_completed: true`, while the trained-model status
   stays AI_UNAVAILABLE until a model is promoted.
