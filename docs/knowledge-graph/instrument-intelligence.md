# Instrument Intelligence — Family Knowledge Profiles

`app/services/instrument_family_profiles.py` defines a knowledge profile
for each of the ten instrument families SPD sees most often, exposed at
`GET /api/knowledge-graph/instrument-families` and
`GET /api/knowledge-graph/instrument-families/{family_key}`.

## Profile contents

Each profile includes:

- **typical_anatomy** — pulled live from
  `app/services/instrument_anatomy.py` (never duplicated as static text)
- **typical_contamination** — the finding types most often seen on this
  family
- **typical_damage** — the structural/condition issues most often seen
- **typical_repair_issues** — what a repair vendor typically fixes for
  this family
- **inspection_priorities** — which zones an inspector should check first
- **cleaning_priorities** — the cleaning steps that matter most for this
  family
- **supervisor_focus_areas** — what a supervisor should specifically
  verify before releasing this family

## The ten families

| Family key | Display name | Anatomy source |
|---|---|---|
| `rigid_scope` | Rigid Scope | `rigid_scope` anatomy family (real, dedicated) |
| `flexible_endoscope` | Flexible Endoscope | `flexible_endoscope` anatomy family (real, dedicated) |
| `kerrison` | Kerrison | `kerrison_rongeur` anatomy family (real, dedicated) |
| `needle_holder` | Needle Holder | `needle_holder` anatomy family (real, dedicated) |
| `scissors` | Scissors | `scissors` anatomy family (real, dedicated) |
| `drill_bit` | Drill Bit | `drill_bit` anatomy family (real, dedicated) |
| `laparoscopic_instruments` | Laparoscopic Instruments | `laparoscopic` anatomy family (real, dedicated) |
| `cannulated_instruments` | Cannulated Instruments | borrows `laparoscopic`'s lumen/cannulated channel zone |
| `orthopedic_instruments` | Orthopedic Instruments | borrows `drill_bit`'s zones |
| `micro_instruments` | Micro Instruments | borrows the generic `default` anatomy family |

## Honest limitation: three borrowed profiles

Cannulated Instruments, Orthopedic Instruments, and Micro Instruments do
not yet have a dedicated anatomy-zone taxonomy split out in
`app/services/instrument_anatomy.py`. Rather than fabricate zones that
were never defined, their profiles borrow the closest existing anatomy
family and carry an `anatomy_family_note` explaining exactly that — surfaced
in the API response and in the Knowledge Graph Explorer UI. This is a
deliberate, documented limitation, not a silent gap:

- **Cannulated Instruments** → borrows `laparoscopic`'s lumen/cannulated
  channel zone. A broader class of cannulated instruments (guide pins,
  cannulated screws, cannulated reamers) exists beyond laparoscopic
  devices; a dedicated split is future work.
- **Orthopedic Instruments** → borrows `drill_bit`'s zones. Orthopedic
  instrumentation beyond drill bits (saws, awls, broaches, impactors) is
  real SPD inventory that doesn't yet have its own zone definition.
- **Micro Instruments** → borrows the generic `default` profile. Fine
  ophthalmic/micro-surgical instruments have distinct handling needs
  (avoiding tip damage during cleaning) that the profile's
  `cleaning_priorities` and `supervisor_focus_areas` capture as text even
  though the anatomy zones themselves are still generic.

**Next step:** when real inspection volume accumulates for these three
families (trackable via the Knowledge Graph Explorer's `instrument`
category and the Pre-Sterilization Command Center's instrument-family
performance), split out dedicated anatomy families in
`instrument_anatomy.py` the same way the other seven were defined, and
update `anatomy_family_key` here to point at the new dedicated family.

## Extending this library

To add an eleventh family: add an entry to
`INSTRUMENT_FAMILY_PROFILES` in `instrument_family_profiles.py` with a
real or borrowed `anatomy_family_key`, then fill in the six knowledge
fields. No manufacturer is ever hardcoded — this mirrors the extensibility
pattern already established in `instrument_anatomy.py`.
