# Inspection #30 — baseline-image resolution decoupled from metadata lookup

**Symptom.** Inspection #30 (reference: ACTIVE Baseline Image #2, Karl Storz) reports
*no manufacturer baseline metadata, no registered baseline image, no ACTIVE baseline
image, no compatible image, no completed comparison, no trained vision model* — even
though Baseline Image #2 is confirmed **ACTIVE** in the Baseline Image Library and the
inspection image bytes are available.

## Confirmed root cause (two code defects)

### 1. Metadata-first early return gated the image resolver
`analyze_inspection()` resolves approved baseline **metadata** first
(`resolve_baseline()` → `BaselineLibraryEntry` with `approval_status="approved"`).
When that returns `baseline_found=False`, the function **early-returned** a
`supervisor_review_required` result with **every baseline-evidence fact hardcoded to
False** and never ran the independent baseline-**image** resolver
(`_live_baseline_comparison` / `resolve_baseline_image`). So a governed **ACTIVE**
reference image was silently ignored whenever its metadata record was absent,
unapproved, or did not match the inspection's declared manufacturer/model. The
baseline-image comparison is logically independent of metadata approval, but the
control flow coupled them.

Reproduced locally: an ACTIVE `BaselineImageLink` (Karl Storz / rigid_scope) whose
parent `BaselineLibraryEntry` is `approval_status="pending"` →
`analyze_inspection` returned `comparison_status="no_approved_baseline"` with all
image facts False, despite the ACTIVE image.

### 2. Cross-table identifier conflation
`_resolve_from_uploaded()` returned an `EnterpriseVendorBaselineSubscription.id` under
the key `baseline_entry_id`. `_baseline_evidence()` then compared that id to
`BaselineImageLink.baseline_library_entry_id` — a **different table's** primary key —
so the "registered image" check could match the wrong link or none.

## Fix

**Decouple (Task 2).** The no-approved-metadata branch now builds the inspection's
candidate identity (manufacturer / model / anatomy / view) and runs the **same
independent, tenant-scoped, compatibility-checked** image resolver the main path uses,
then derives the seven provenance facts from the real result. `manufacturer_baseline
_metadata_found` stays `False` (honest), while `baseline_image_registered / active /
compatible / real_image_comparison_completed` reflect the real ACTIVE reference image
and comparison whenever one resolves. **Clinical scoring stays independently governed**
(no approved metadata ⇒ supervisor review / `AI_UNAVAILABLE`), and human review stays
mandatory; visual similarity never authorizes release.

**Typed identifiers (Task 3).** `resolve_baseline()` now exposes explicit, typed keys:
`baseline_library_entry_id` (a real `BaselineLibraryEntry` id — the only id compared to
`BaselineImageLink.baseline_library_entry_id`) and `vendor_subscription_id` (the
uploaded-baseline subscription id). The uploaded path sets
`baseline_library_entry_id=None`, so a subscription id can never be mistaken for a
library-entry id. (`baseline_entry_id` is retained only as a legacy alias.)

## Local evidence (fixed)

Inspection with an ACTIVE compatible reference image but **no approved metadata**:

```
manufacturer_baseline_metadata_found = False
baseline_image_registered = True
baseline_image_active = True
baseline_image_compatible = True
inspection_image_bytes_available = True
real_image_comparison_completed = True
comparison_status = exact_match        similarity = 1.0   method = sha256_exact
ai_analysis.status = AI_UNAVAILABLE     human_review_required = True
analysis_status = supervisor_review_required   (clinical scoring still governed)
```

## Independent scoring states (Task 4)

- **Visual comparison:** `exact_match`, `comparable`, `materially_different`,
  `no_approved_baseline`, `incompatible_instrument`/`incompatible_view`,
  `insufficient_quality`, `baseline_integrity_failed`. A successful comparison exposes
  numeric similarity, comparator method + version, baseline-image link id, integrity
  verification (hash-checked on load), and the "not verified cleanliness" limitation.
- **AI defect analysis:** `AI_UNAVAILABLE` when no eligible trained model exists.
  Cleanliness / debris / corrosion / damage are **never** inferred from average-hash
  similarity.
- **Clinical disposition:** requires authorized human review; similarity alone never
  authorizes release.

## Frontend (Task 5)

Three separated panels on the New Inspection result:
- **A. Manufacturer Reference Comparison** — rendered **independently** of the AI /
  clinical state whenever a comparison completes: visual similarity %, method,
  reference-image id, and the identical-image / not-cleanliness limitation.
- **B. AI Defect Detection** — verified model findings or `AI_UNAVAILABLE`.
- **C. Human Inspection & Disposition** — manual observations, review requirements,
  authorized decisions.

The supervisor-review notice no longer says risk "scoring is locked" in a way that
implies image similarity cannot be calculated: it now states that **clinical** risk
scoring is withheld pending a baseline override, and that the manufacturer
reference-image visual comparison is calculated independently.

## Regression coverage (Task 6)

`tests/test_inspection_30_baseline_resolution.py` (11 scenarios): identical ACTIVE
reference → 100%; different photos → real (non-fabricated) similarity; **metadata
absent + ACTIVE compatible image → independent resolution succeeds (the #30 fix)**;
incompatible manufacturer → no comparison; cross-tenant ACTIVE image → denied;
inactive (never-activated) reference → no comparison; missing image bytes → explicit
unavailable status; no trained model → comparison still runs, AI unavailable; human
review mandatory; clinical PDF renders; typed identifiers never conflate tables.

## Production acceptance (operator)

This sandbox cannot reach `*.onrender.com`. After deploy of this change onto the
branch Render actually builds:
1. Re-run Inspection #30's instrument with the same photo as the ACTIVE reference and
   read the raw `/api/inspections/<id>` response: expect
   `baseline_evidence.baseline_image_active=true`,
   `real_image_comparison_completed=true`, `comparison_status=exact_match`,
   `ai_analysis.baseline_image_similarity.similarity=1.0`.
2. Confirm Baseline Image #2's `BaselineImageLink` is ACTIVE for the inspection's
   tenant and that its manufacturer/model/anatomy are compatible — "ACTIVE" alone does
   not guarantee compatibility; an incompatible instrument correctly yields no
   comparison.
