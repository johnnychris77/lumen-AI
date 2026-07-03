# Guided Capture Workflow (v1.2)

Walks a technician through the required images for an instrument before AI
analysis: which zone to capture next, the recommended camera angle/lighting/
focus, and a plain-language instruction — built entirely on the existing
Anatomy Library and Coverage Engine (see `docs/instruments/anatomy-library.md`
and `docs/instruments/coverage-engine.md`); no new zone-assignment logic.

## Source of truth

`backend/app/services/guided_capture.py`

- `ZONE_CAPTURE_GUIDANCE` — per-zone camera angle / lighting / focus /
  instruction sentence for the commonly-named zones (o-ring area, drill-bit
  flute, box lock, serrations, hinge, distal tip/end, lens edge, threaded
  region, biopsy/suction/working channel, ratchet, insulation edge, sheath
  connection). This is instructional UI copy (camera technique), not a
  clinical claim, so it's authored directly.
- `_CATEGORY_FALLBACK` — generic angle/lighting/focus guidance keyed by the
  zone's `zone_category` (from `instrument_anatomy.py`) for zones without a
  specific entry — honest, not fabricated zone-specific detail.
- `zone_capture_guidance(instrument_type, zone_name)` — resolves guidance for
  one zone, falling back to category-level, then a generic default.
- `capture_checklist(instrument_type, captured_zones)` — required / optional /
  captured / missing / high-risk zones.
- `guided_capture_panel(instrument_type, captured_zones)` — the full panel
  payload: family, checklist, the next zone to capture (missing required
  zones, high-risk first), and that zone's capture guidance.

## API

`GET /api/guided-capture/{instrument_type}?captured_zones=a,b,c` — Guided
Capture Panel + Capture Checklist + Coverage Score/readiness in one response.
`captured_zones` omitted means "not yet assessed" (coverage is honestly
`not_assessed`, not 0%); an explicit (possibly empty) list is assessed
normally.

## Frontend

`frontend/src/components/GuidedCapturePanel.tsx`, rendered inside
`NewInspectionPage.tsx` next to the zone-tagging checklist. Shows:

1. Coverage score/status
2. The next zone to capture, with its recommended angle/lighting/focus and
   instruction sentence (e.g. "Capture close-up of o-ring area.")
3. The full checklist (required/optional/captured/missing/high-risk zones)
4. The AI Analysis Gate banner when coverage is insufficient (see
   `coverage-gate-rules.md`)

## Next-zone prioritization

Missing required zones are offered in order, high-risk zones first — the
technician is guided to close the highest-risk gaps before lower-risk ones.
