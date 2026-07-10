# Inspection Session — API Reference

## `GET /api/inspections/{id}/vision-session`

Roles: admin, spd_manager, supervisor, operator, viewer.

Returns the full multi-image session view for one inspection:

| Field | Source |
|---|---|
| `images` | Every `InspectionImageTag` row for this inspection |
| `image_timeline` | Capture-ordered sequence with quality band + flag state (Objective 8) |
| `missing_anatomy` | Coverage Engine's missing required zones, phrased as "You have not captured the X." (Objective 5) |
| `duplicate_detection` | Duplicate images / wrong anatomy / wrong instrument findings (Objective 4) |
| `cross_image_reasoning` | Per-finding zone correlation + one overall result across all images (Objective 6) |
| `evidence_fusion` | The fused clinical recommendation (Objective 7) |

`predicted_findings` used by cross-image reasoning and evidence fusion are
reconstructed from `InspectionFinding` — the real per-finding rows already
persisted at analysis time (`app/routes/inspections.py`) — not a re-run of
the scoring engine. Per-finding `confidence` (v2.3) is persisted on the same
row and read back verbatim; rows logged before the column existed carry
`null` rather than a fabricated value.

## `GET /api/inspections/{id}/gallery`

Roles: admin, spd_manager, supervisor, operator, viewer.

Objective 9 — Inspection Gallery: every captured image, grouped by
`anatomy_zone`. Each image carries its quality band, flag state, and
technician — everything the Gallery's zoom/compare/flag/download affordances
need. (See `docs/vision/vision-fusion.md` for what "compare" means here —
this platform doesn't retain raw image bytes by default, so "zoom"/"compare"
operate on the same structured metadata every other view uses, not on pixel
content that was never stored.)

## `POST /api/inspections/{id}/images/{tag_id}/flag`

Roles: admin, spd_manager, supervisor.

```json
{"flagged": true, "reason": "duplicate of image #4"}
```

Flags (or clears the flag on) one captured image. Does not delete the image
or its metadata — a flagged image still appears in the timeline and
gallery, marked accordingly.

## Submitting per-image metadata

`POST /api/inspections`'s existing `image_view_tags` array (v1.2) gained
three v2.2 fields — see `multi-image-reasoning.md` for the full example.
