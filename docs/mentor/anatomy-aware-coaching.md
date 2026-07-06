# Anatomy-Aware Coaching (v1.4)

## What it does
`spd_mentor_engine.anatomy_coaching(result)` returns technician-facing
coaching sentences tied to the instrument's actual anatomy profile
(`result.instrument_anatomy`, from the Phase 15 Instrument Anatomy Library) —
never generic filler.

## Canned phrasing for well-known SPD lore
A small set of instrument families have specific, widely-recognized SPD
coaching phrases (`_FAMILY_COACHING_PHRASES`):

- **Kerrison rongeur**: "Kerrison jaw serrations are high-retention anatomy
  zones." / "Open the box lock and actuate the hinge during inspection — soil
  hides in the pivot."
- **Rigid scope**: "Rigid scope O-ring regions frequently retain organic
  material." / "Inspect the working channel and seal closely; these are
  high-retention zones."
- **Drill bit**: "Drill-bit flutes require careful brushing." / "Threaded
  regions between the flutes are a common site for retained residue."
- **Needle holder**: "Needle-holder box locks should be opened during
  inspection." / "Jaw inserts and serrations are high-retention anatomy
  zones."

## Generated fallback
For every other instrument family (laparoscopic, general forceps, scissors,
flexible endoscope, and anything unclassified), coaching sentences are
generated from the instrument's own zone data: any zone with
`retention_risk == "high"` (or listed in `high_risk_zones`) produces
`"{category} {zone_name} is a high-retention anatomy zone."` — always derived
from the actual anatomy profile, never invented per-instrument detail.

## Zone descriptions (Training Mode)
When Training Mode is on, every anatomy zone for the instrument gets an
explanation via `_zone_description()`, which reuses
`instrument_zones.ZONE_INFO`'s per-zone reason (falling back to a generic
retention-risk sentence for zones without a specific entry).
