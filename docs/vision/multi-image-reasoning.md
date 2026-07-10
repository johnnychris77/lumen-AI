# Multi-Image Inspection Session

LumenAI Inspect v2.2 — "Project Vision 360." Mission: transform LumenAI from
a single-image inspection engine into a multi-image clinical reasoning
engine, where the AI combines multiple inspection views before generating
its clinical recommendation.

## What already existed

v1.2's Guided Capture (`app/models/inspection_image_tag.py`,
`app/services/guided_capture.py`) already supported multiple tagged images
per inspection — each `InspectionImageTag` row records an `anatomy_zone`,
`image_view`, `capture_quality`, and optional notes, and
`app/services/inspection_coverage.py`'s Coverage Engine already computed
required-zone coverage and missing-image guidance from the set of captured
zones. v2.2 builds on this rather than duplicating it.

## What v2.2 adds

- **Per-image identity and timestamps**: `technician`, `sequence` (capture
  order), and a real per-image `image_sha256` (previously only an
  inspection-level hash existed, shared across every tag — duplicate
  detection needs one hash per image).
- **Image Quality Intelligence**: a deterministic `quality_score` (0-100)
  and `quality_band` (excellent/good/acceptable/poor/reject), computed at
  capture time from the image's own hash (see `image-quality-engine.md`).
- **A flag**: `flagged`/`flag_reason`, so a supervisor or technician can
  mark an image for recapture/review without deleting it.

## The session model

One `Inspection` row is the session; its `InspectionImageTag` rows are the
session's captured images. `GET /api/inspections/{id}/vision-session`
returns the full multi-image view:

```
{
  "image_timeline": [...],       // Objective 8
  "missing_anatomy": {...},      // Objective 5
  "duplicate_detection": {...},  // Objective 4
  "cross_image_reasoning": {...},// Objective 6
  "evidence_fusion": {...},      // Objective 7
}
```

See `inspection-session.md` for the API contract, `image-quality-engine.md`
for the quality-scoring model, and `vision-fusion.md` for cross-image
reasoning and evidence fusion.

## Submitting a multi-image session

`POST /api/inspections` already accepted an `image_view_tags` array (v1.2);
v2.2 adds `image_sha256`, `technician`, and `sequence` to each tag:

```json
{
  "instrument_type": "kerrison_rongeur",
  "image_view_tags": [
    {"anatomy_zone": "jaw", "image_view": "jaw close-up", "image_sha256": "…", "technician": "jsmith"},
    {"anatomy_zone": "box lock", "image_view": "box lock open", "image_sha256": "…", "technician": "jsmith"}
  ]
}
```

Each tag is scored for quality at creation time
(`app/services/image_quality_engine.py`) and persisted with its own
`quality_score`/`quality_band` — nothing is re-scored later, so the same
image always has the same score.
