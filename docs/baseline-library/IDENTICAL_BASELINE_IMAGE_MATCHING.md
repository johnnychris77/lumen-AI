# Identical manufacturer baseline image — exact-match verification

**Scenario.** The same photograph is uploaded as the approved manufacturer
reference AND as the new inspection image. Expected: 100% visual similarity, an
exact match — surfaced honestly, never as proof of cleanliness.

The operator-supplied original file SHA-256 was
`0eed6967028cf31dbb5139ee85986cae39c94f2bf9b7d869771ccc2790c9f154` (the hash of
the *original* bytes, before any normalisation).

## Task 1 — how identical bytes reach the comparator

Both the baseline-reference path and the inspection path normalise bytes the same
way before they are ever stored or compared:

- **Baseline reference** → `baseline_image_registration_service` →
  `image_retention_service.retain_reference_image` → `strip_exif(data)` → stored
  reference bytes.
- **Inspection image** → `inspection_image_processing_service.store_processing_image`
  → `strip_exif(data)` → temporary processing bytes.

`strip_exif` re-encodes from pixel data only (drops EXIF/GPS/ICC) and is
**deterministic** for a given input and Pillow version. So the operator's
original file hash (`0eed6967…`) is *not* what the comparator sees — it is the
pre-strip client key. What the comparator sees is the EXIF-stripped
(`stored_sha256`) bytes, and because **both sides strip the same original the
same way, the two stored byte sequences are byte-identical**. The processing
store records this explicitly: `image_sha256` (original/client key) vs
`stored_sha256` (cleaned-bytes integrity key).

## Task 2 — the real comparator was executed on the two stored sequences

`image_similarity_service.compare_image_bytes` short-circuits on a SHA-256 match
of its two inputs. Run end to end through the **real HTTP routes** (upload +
`POST /api/inspections`) with the same photo on both sides, the recorded result
is exactly:

```json
{"status": "exact_match", "similarity": 1.0, "hamming_distance": 0,
 "method": "sha256_exact", "comparator_version": "lens-average-hash-v1"}
```

There is **no comparator defect**. The comparator recognises the identical pair
and returns a true exact match.

### One hardening applied (the only confirmed code correction)

The sha256 short-circuit previously ran **before** decoding either input, so two
byte-identical *non-images* would have been reported `exact_match`. Per the
requirement to *validate that both inputs decode as images before accepting an
exact match*, `compare_image_bytes` now decodes both (computes the perceptual
hash, which fails closed to `insufficient_quality` on a non-image) **first**, and
only then applies the sha256 exact-match short-circuit. Byte-identical real
images are unaffected — still `sha256_exact` / 1.0.

## Task 3 — the exact match flows through every surface

End-to-end evidence (real routes, JWT/admin, baseline governed to ACTIVE through
the real service layer):

```
UPLOAD: processing_available = true
ai_analysis.baseline_image_similarity:
  status=exact_match  similarity=1.0  is_image_comparison=true
  method=sha256_exact  comparator_version=lens-average-hash-v1  baseline_id=<link id>
baseline_evidence:
  manufacturer_baseline_metadata_found=true  baseline_image_registered=true
  baseline_image_active=true  baseline_image_compatible=true
  inspection_image_bytes_available=true  real_image_comparison_completed=true
  comparison_status=exact_match  trained_vision_model_available=false
Persisted row: baseline_comparison_status=exact_match similarity=1.0
  method=sha256_exact baseline_image_link_id=<link id>
Honest safety: ai status=AI_UNAVAILABLE  authorizes_release=false
  human_review_required=true  predicted_findings=[]  inspection_score=None
```

The New Inspection page now renders, for an exact match:

> **Manufacturer baseline visual similarity:** 100% — exact same image
> (method sha256_exact, reference image #&lt;id&gt;). *Identical-image matching is
> not proof of cleanliness — a qualified person must still complete the
> inspection.*

(method + reference-image id + the identical-image caveat). The generic
"Baseline visual comparison available." one-liner is no longer the exact-match
surface.

## Task 4 — regression coverage

`tests/test_identical_baseline_image_matching.py` (10 scenarios): comparator
identical-bytes exact match; the decode gate (identical non-image bytes →
`insufficient_quality`, never `exact_match`); re-encoded copy is highly similar
but **not** exact (byte identity required); `compare_against_baseline` threads
`baseline_id`/version through an exact match; and six end-to-end scenarios —
similarity surface, `baseline_evidence`, persisted columns, no-release safety,
trained-model-still-unavailable, and the clinical PDF rendering.

## `/api/health` — the real route, deployment verification + honest readiness

The served `/api/health` is **`app/routes/system.py`** (`/health` under the `/api`
prefix), *not* `app/routes/health.py` (which is never included — dead code). The
real route now returns:

- `git_commit` — so an operator can confirm which commit production is actually
  running without dashboard access (`RENDER_GIT_COMMIT` / `GIT_COMMIT` / … /
  `unknown`).
- `schema_ok` + `status` — the startup schema-bootstrap outcome, reported
  **truthfully**. If a comparison-critical table/column
  (`inspection_processing_images`, `baseline_image_links`,
  `inspections.baseline_comparison_status`) is missing, `status` is
  `"degraded"` (never `"ok"`) with sanitized `schema_issues`. A health check can
  therefore never certify readiness while the app would silently serve
  "no comparison performed".

Startup stays **fail-open** (a schema error must not crash the process — on
Render that fails the deploy's health check and silently keeps the OLD build
live, which is the stale-deploy failure mode behind Inspections #14–#18). HTTP
stays 200 so the new build is observable; the *body* carries the truth. Full
exceptions stay in the logs, not the public health body.

## Task 5 — production acceptance (operator step)

This sandbox cannot reach `*.onrender.com`. The backend and comparator are
verified correct locally. Operator checks:

1. `GET https://<backend>.onrender.com/api/health` → read `git_commit`
   (confirm it matches the merged commit) **and** `schema_ok`/`status`. If
   `status` is `"degraded"`, the listed `schema_issues` name the missing
   table(s); if `git_commit` does not match the merge, the backend is stale —
   redeploy/restart (schema bootstraps at startup, so new processing
   table/columns only appear after a restart onto the merged code).
2. Re-run the identical-image inspection and inspect the raw API response: if
   `analysis.baseline_evidence` is **absent**, the backend is stale (step 1); if
   present with `real_image_comparison_completed=true` and
   `comparison_status=exact_match`, the exact match is working.

### Inspection #22 (rotary orthopedic) — "no comparison" is expected without an ACTIVE reference image

When a manufacturer **metadata** record resolves but **no ACTIVE reference
image** is registered for the instrument, the backend returns a fully populated
`baseline_evidence` with `baseline_image_registered=false`,
`comparison_status="no_approved_baseline"`, and the current frontend shows the
*specific* message *"Manufacturer image not registered — the approved baseline is
a library record only…"* (not the generic line). The exact-match 100% result
requires an **ACTIVE** manufacturer reference **image** governed for that same
instrument (DRAFT → PENDING_REVIEW → APPROVED → ACTIVE). "Baseline Source:
Manufacturer" proves only a metadata record, not a reference image.
