# Guided Capture — Image View Selection in New Inspection

After a technician selects an instrument type in the New Inspection workflow,
LumenAI Inspect resolves that instrument's required anatomy zones and asks
the technician to tag which zones their images actually cover, before AI
analysis runs.

## Where it lives

`frontend/src/pages/NewInspectionPage.tsx`

1. On `instrument_type` change, the page calls
   `GET /api/instrument-anatomy/{instrument_type}` and loads
   `zone_names` into `anatomyZones` state.
2. A "Zones inspected" checklist renders one checkbox per anatomy zone
   (`inspectedZones` state) — this **is** the image-view-capture step: each
   checked zone represents an image view the technician captured for that
   zone.
3. On submit, `inspected_zones` is sent to `POST /api/inspections` alongside
   the instrument/image data.

## Per-family recommended views

The zone lists a technician tags against come directly from
`instrument_anatomy.py`'s `required_images` / zone names per family, e.g.:

- **Rigid scope**: distal tip, lens edge, o-ring area, light post, eyepiece,
  working channel, sheath connection, seal.
- **Flexible endoscope**: distal end, bending section, insertion tube,
  suction channel, biopsy channel, air/water nozzle, light guide lens,
  control body.
- **Drill bit**: tip, flutes, threaded region, cutting edge, shank, hub.
- **Kerrison/rongeur**: jaw, serrations, box lock, hinge, spring, ratchet,
  handle.
- **Scissors**: tip, blade, cutting edge, serration, box lock, handle.
- **Needle holder**: jaw inserts, serrations, box lock, ratchet, tungsten
  carbide inserts, handle.

These names are the canonical zone vocabulary used across anatomy
resolution, zone-aware scoring, and the Coverage Engine — the v1.1 spec's
requested view names (e.g. "cutting tip", "jaw serration", "channel opening")
map onto this existing vocabulary rather than introducing a second,
parallel naming scheme that would fork zone data already in production
(`inspected_zones_json` on stored inspections uses these names).

## Non-blocking by design

Missing high-risk zones surface as guidance ("Inspection coverage incomplete.
Upload additional images for: …" — see `coverage-engine.md`), not a hard
block. Org policy that requires full coverage before submission is a future
extension point, not the current default.
