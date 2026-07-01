# Inspection Coverage Engine (Phase 15)

## What it does
Given an instrument's anatomy and the zones the technician captured/inspected,
computes an **Inspection Coverage Score**, a quality band, the missing required
zones, and "still needed" image guidance.

## Inputs
- `instrument_type` → resolves to an anatomy family with `required_images`.
- `inspected_zones` — technician-tagged zones (a checklist). Not CV-detected today.

## Output
- `overall_coverage` (% of required zones inspected)
- `inspected`, `inspected_required`, `missing`
- `quality`: complete / acceptable / incomplete / insufficient
- `message` when required zones are missing:
  "Inspection incomplete. Upload additional images for required high-risk zones."
- Missing-image guidance: "Close-up image of {zone}" per missing required zone.

## Required zones (configurable by instrument type)
Defined per family in the Instrument Anatomy Library `required_images`. Extend or
override per manufacturer/model via the Instrument Knowledge Library.

## Risk map
Per-zone: zone · required? · inspected? · findings? · zone risk · recommended
manual check. Text/card form today; SVG/overlay/heatmap are a future CV release
(nothing fabricated).
