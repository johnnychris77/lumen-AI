# Image View Tagging & Capture Quality Standards (v1.2)

Every image uploaded during Guided Capture is tagged with which anatomy zone
and image view it depicts, plus a technician-assessed capture quality and
optional notes — metadata about the *view*, not pixel-level detection (the
same honesty convention as the rest of the anatomy/coverage engine).

## Source of truth

`backend/app/models/inspection_image_tag.py` — `InspectionImageTag`:

| Field | Meaning |
|---|---|
| `instrument_family` | The instrument family this image belongs to |
| `anatomy_zone` | Which anatomy zone the image depicts |
| `image_view` | The specific camera view (often the zone name; can differ, e.g. "end-on" vs. "side profile" of the same zone) |
| `capture_quality` | Technician's own assessment — see values below |
| `notes` | Optional free-text (e.g. "residue visible, recommend re-clean") |

### Capture quality values

`CAPTURE_QUALITY_VALUES = ("good", "acceptable", "poor", "unusable")`

- **good** — in focus, correctly lit, zone fully visible.
- **acceptable** — usable for review; minor blur/glare/framing issues.
- **poor** — hard to assess; recommend re-capture if the zone is high-risk.
- **unusable** — not usable for review; does not count toward coverage.

Quality is self-reported by the technician at capture time — this is not an
automated image-quality classifier (a related but separate capability; see
`docs/ai/instrument-zone-detection-training-plan.md` for the future CV plan).

## API

- `POST /api/inspections` — accepts `image_view_tags: ImageViewTagIn[]`
  alongside the existing `inspected_zones` checklist; each tag is persisted as
  an `InspectionImageTag` row linked to the new inspection.
- `GET /api/inspections/{id}/image-tags` — list an inspection's image tags.

## AI context

`analyze_inspection()` accepts `image_view_tags` and passes them straight
through into the analysis result under `"image_view_tags"` — the AI context
reflects exactly what was tagged, without altering scoring logic (tags are
metadata/labels, not a clinical decision input).

## Frontend

Per-image tagging UI in `NewInspectionPage.tsx`: one row per uploaded image
(zone, image view, quality, notes), keyed by filename+size so tags survive
re-renders without depending on array index.
