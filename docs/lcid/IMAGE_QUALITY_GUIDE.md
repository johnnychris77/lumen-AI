# LCID Image Quality Guide

## Grades

The LCID spec's five grades — Excellent, Good, Acceptable, Poor, Reject —
map onto the existing, real, pixel-computed grades in
`app.models.dataset_governance.IMAGE_QUALITY_LEVELS`:

| LCID spec grade | Codebase constant |
|---|---|
| Excellent | `QUALITY_EXCELLENT` |
| Good | `QUALITY_GOOD` |
| Acceptable | `QUALITY_MARGINAL` |
| Poor | `QUALITY_POOR` |
| Reject | `QUALITY_REJECT` |

("Marginal" was the original sprint's name for this band; "Acceptable" is
this sprint's synonym for the same grade — not a new, sixth grade.)

## Computation

Every score is computed from real image bytes via Pillow
(`app.services.ml.image_quality`) — brightness, sharpness, resolution,
and derived blur/lighting/exposure/focus/cropping/visibility flags — never
a fabricated or guessed grade. See `docs/ml-governance/DATA_GOVERNANCE.md`
for the exact thresholds.

## Enforcement

`Reject`-graded images remain registered and searchable
(`images/rejected/` in the filesystem tree) but
`app.services.ml.dataset_builder.eligible_entries()` excludes them from
every training export unconditionally — there is no override path.
