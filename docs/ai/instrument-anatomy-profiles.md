# Instrument Anatomy Profiles

Source of truth: `backend/app/services/instrument_anatomy.py`
(`INSTRUMENT_ANATOMY`, `resolve_family`, `get_anatomy`, `anatomy_profile`).

The Anatomy Profile Service takes an instrument's identity hints
(`instrument_type`, optional `instrument_name`, `manufacturer`, `model`) and
returns:

- `instrument_family` (or `unknown`)
- `anatomy_zones` / `zone_names`
- `required_zones` / `recommended_image_views`
- `high_risk_zones`
- `zone_descriptions` (per-zone honest one-liner)
- `contamination_risks` / `condition_risks` (per zone)
- `manual_check_steps`
- `warning` — set when the family is `unknown`

## Families and their zones

| Family | High-risk / retention zones |
|---|---|
| **rigid_scope** | distal tip, lens edge, **o-ring area**, light post, working channel, sheath connection, seal |
| **flexible_endoscope** | distal end, bending section, **suction channel**, **biopsy channel**, air/water nozzle, light guide lens |
| **drill_bit** | tip, **flutes**, **threaded region**, cutting edge, hub |
| **kerrison_rongeur** | jaw, **serrations**, **box lock**, hinge, spring, ratchet |
| **scissors** | tip, blade, cutting edge, serration, box lock |
| **needle_holder** | jaw inserts, serrations, box lock, ratchet |
| **laparoscopic** | distal jaws, hinge, **insulation edge**, shaft, handle seam, lumen/cannulated channel |
| **general_forceps** | jaws, serrations, box lock, hinge, ratchet |
| **unknown** | working surface, hinge/joint, box lock (generic SPD profile) + warning |

## Rigid vs flexible endoscope

The two are deliberately distinct. Flexible endoscopes are declared *before*
rigid scopes so their keywords (`colonoscope`, `gastroscope`, `bronchoscope`,
`duodenoscope`, `flexible …`) resolve first; a rigid scope's generic
`scope`/`endoscope` match would otherwise swallow them. A rigid scope reasons
about the **o-ring area / lens edge / sheath connection**; a flexible endoscope
reasons about **internal channels (biopsy, suction) / distal end / bending
section**.

## Extending

Add a family by inserting an entry into `INSTRUMENT_ANATOMY` with `match`
keywords and `_zone(...)` definitions. No manufacturer is hardcoded; per-site
manufacturer/model knowledge is layered via the `InstrumentKnowledge` table.
