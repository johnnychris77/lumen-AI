# Image Quality Intelligence

`app/services/image_quality_engine.py`.

⚠️ **Deterministic placeholder — not production computer vision.** Scores
every captured image across the eight metrics the sprint specifies, seeded
from the image's own SHA-256 hash — the same "stable pseudo-value" pattern
`baseline_comparison_scoring_service._seed_from`/`_pseudo` already uses for
the rest of the platform's deterministic-placeholder scoring, so the same
image always scores the same and nothing is fabricated independently of
that seed. A future real-CV release drops into the same per-metric contract
without changing any caller.

## Metrics

Focus, Blur, Lighting, Exposure, Glare, Field Coverage, Obstruction,
Perspective — each scored 0-100, biased toward the 55-100 range (a real
captured image is usually usable; a genuinely bad one is the exception, not
scored as a coin flip).

## Bands

| Overall score | Band |
|---|---|
| ≥ 90 | Excellent |
| ≥ 75 | Good |
| ≥ 55 | Acceptable |
| ≥ 30 | Poor |
| < 30 | Reject |

`poor`/`reject` set `human_review_required: true` on the score result.

## When there's no real image hash

`score_image(image_sha256, fallback_key=...)` falls back to a stable seed
derived from `fallback_key` (e.g. `f"{inspection_id}:{anatomy_zone}:{sequence}"`)
when no per-image hash is supplied — so two untagged images in the same
session still get distinguishable, deterministic scores instead of an
identical fabricated value.

## When scoring happens

Once, at capture time (`POST /api/inspections`, when `image_view_tags` is
present) — the score is persisted on the `InspectionImageTag` row
(`quality_score`, `quality_band`), never recomputed differently later.
