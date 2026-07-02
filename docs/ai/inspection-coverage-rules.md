# Inspection Coverage Rules

Source of truth: `backend/app/services/inspection_coverage.py`
(`compute_coverage`, `missing_image_guidance`, `build_risk_map`).

## What it computes

For an instrument family and the technician-tagged inspected zones:

- `required_zones` (total) — from the anatomy profile's `required_images`
- `inspected_required` — required zones that were tagged
- `missing` — required high-risk zones not yet captured
- `overall_coverage` — % of required zones captured
- `quality` / coverage status:
  - **complete** — no missing required zones and ≥95%
  - **acceptable** — no missing required zones, or ≥80%
  - **incomplete** — ≥50%
  - **insufficient** — <50%
  - **not_assessed** — zones were not tagged (reported honestly, not as 0%)

## Missing-zone guidance

When required high-risk zones are missing, the UI shows:

> "Inspection coverage incomplete. Upload images for: [missing zones]."

`missing_image_guidance` returns a "Close-up image of {zone}" line per missing
required zone. It is empty when zones were not tagged (no nagging on untagged
inspections).

## Not a submission gate

Coverage is advisory. It does **not** block submission unless an organization
explicitly configures a hard gate. This keeps the pilot usable while still
surfacing incomplete inspections for supervisor attention.

## not_assessed vs 0%

When `inspected_zones` is `None` (the technician did not tag zones), coverage is
`not_assessed` with `overall_coverage: null` — deliberately **not** an alarming
0%. An explicit (possibly empty) list is assessed normally.

## Risk map

`build_risk_map` emits a per-zone row (zone · required? · inspected? · findings ·
zone risk · recommended manual check) — a text/card map. Visual anatomy overlays
and heatmaps are a future CV release and are not fabricated.
