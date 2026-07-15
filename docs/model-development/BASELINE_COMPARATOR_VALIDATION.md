# Baseline Comparator Validation — Project Lens

## What existed before (confirmed via trace, Section 17/18)

Repo-wide grep for `structural_similarity|phash|imagehash|cosine|embedding|
ssim` returned zero real results before this sprint. Every "similarity"/
"match" number shown anywhere in this codebase (`baseline_match_score` in
`baseline_comparison_scoring_service.analyze_inspection()`) came from
SHA-256-seeded pseudo-random arithmetic — never a pixel comparison. This
was directly confirmed, not assumed: `image_sha256` is a real value
derived from real uploaded bytes (the frontend correctly threads it
through from the upload step, `NewInspectionPage.tsx:463,496`), so
different images do get different seeds and different scores — but the
"score" itself has never been a function of actual visual similarity.

## What this sprint adds

`app.services.ml.image_similarity_service` — a real, pure-Python (no
numpy/scipy) 64-bit average-hash (aHash) perceptual comparator:

1. `compute_average_hash()` — downscale to 8×8, grayscale, threshold
   against the mean pixel value, producing a 64-bit hex hash from real
   pixel data.
2. `hamming_distance()` / `similarity_from_distance()` — real bit-distance
   comparison, `similarity = 1 - distance/64`.
3. `compare_image_bytes()` — exact-sha256 match short-circuits to
   `exact_match` (similarity 1.0); otherwise the aHash distance decides
   `comparable` vs. `materially_different` against a disclosed, fixed
   threshold (20 of 64 bits) — not fit to any dataset (none exists to fit
   against).
4. `compare_against_baseline()` — the full Section 18 flow: **validates
   compatibility first** (instrument family, manufacturer) — an
   incompatible pair never receives a similarity number
   (`incompatible_view`); no baseline available returns
   `no_approved_baseline`; missing image bytes for either side returns
   `insufficient_quality` — only a compatible pair with real bytes on both
   sides ever gets a real similarity score.

## Verified distinctions (Section 18's requirement)

| Scenario | Test | Result |
|---|---|---|
| Exact same image | `test_exact_same_image_produces_exact_match` | `status=exact_match`, `similarity=1.0` |
| Visually different image | `test_visually_different_image_does_not_reuse_first_result` | differs from the same-image result |
| No approved baseline | `test_no_approved_baseline_returns_no_approved_baseline` | `status=no_approved_baseline`, `similarity=None` |
| Incompatible instrument family | `test_incompatible_instrument_family_does_not_receive_fabricated_similarity` | `status=incompatible_view`, `similarity=None` |

Near-duplicate and insufficient-quality cases were additionally verified
during development (see `MANUAL_MODEL_ACCEPTANCE.md` Cases 2 and 7 for the
disclosed manual walkthrough).

## What this comparator does not claim

- Not a learned embedding — a hand-computed perceptual hash, disclosed as
  a genuine "first-stage method" per Section 18's own guidance ("Possible
  first-stage methods: perceptual image hash...").
- No numeric similarity is ever produced for an incompatible or
  unavailable comparison — enforced structurally
  (`compare_against_baseline()` returns before computing any hash in
  those branches).
- Never described as a cleanliness or sterility score — this module
  computes pixel similarity only; any clinical interpretation remains the
  Decision Engine's responsibility, unchanged by this sprint.

## Integration point

`live_inference_adapter.predict()`'s `baseline_comparison` field is
currently `None` in the live contract — wiring a specific baseline
image's bytes into that field (resolving via
`app.services.baseline_comparison_service.compare_to_baselines()`'s
already-real baseline-record resolution, then calling
`compare_against_baseline()` on the resolved record's bytes) is the
direct next integration step once a real promoted model and real baseline
image bytes both exist for a given tenant; the comparator itself is fully
built, tested, and ready for that wiring.
