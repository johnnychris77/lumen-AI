# Clinical Rules — Cleaning Knowledge Library & Recommendation Mapping

## Cleaning Knowledge Library (Phase 21 §4)

`app/services/cleaning_knowledge.py::CLEANING_KNOWLEDGE` stores, for every
anatomy zone in `app/services/instrument_zones.py::ZONE_INFO`:

| Field | Meaning |
|---|---|
| `cleaning_method` | The recommended manual cleaning approach for this zone. |
| `brush_type` | What kind of brush (and why — e.g. "soft brush; abrasive tools can damage the insulation"). |
| `flushing_requirement` | Whether/how the zone needs flushing (lumens/channels: mandatory; surface zones: not applicable). |
| `ultrasonic_guidance` | Whether ultrasonic cleaning is recommended, and any caveats. |
| `visual_inspection_guidance` | How to visually inspect the zone (magnification, borescope, etc.). |
| `manual_verification_guidance` | How to confirm the zone is actually clean before moving on. |

**This is explicitly not an IFU replacement.** Every response from
`get_cleaning_knowledge(zone)` carries the note: *"Advisory clinical
knowledge, not an IFU replacement — the device IFU governs when the two
differ."* This is a clinical knowledge layer, paraphrased general SPD
practice (in the same spirit as `clinical_mentor.py`'s existing
`FINDING_EDUCATION` library) — never a specific manufacturer's written
instructions.

Coverage: all 18 zones in `ZONE_INFO` have a dedicated entry
(`serrations`, `grooves`, `box lock`, `hinge`, `ratchet`, `drill-bit
flute`, `threaded region`, `lumen opening`, `inner channel`, `biopsy
channel`, `suction channel`, `air/water nozzle`, `o-ring area`, `rigid
scope port`, `insulation edge`, `cutting edge`, `surface discoloration
area`, `unspecified region`) plus a fallback for any zone name not in the
list.

## Recommendation mapping (generic, severity-unaware queries)

For the Knowledge Graph Explorer's `reasoning_chain()`, where no real
scored inspection exists, the finding type is mapped to one of the five
frozen decision-engine outcomes conservatively:

| Finding category | Outcome | Rationale |
|---|---|---|
| Contamination (`blood`, `bone`, `tissue`, `debris`, `other`, `other_organic_residue`) | `REPROCESS` | Contamination findings are, by default, addressed by recleaning — see the real scoring engine's `recommended_action()` in `baseline_comparison_scoring_service.py`. |
| `crack`, `missing_component` | `REMOVE FROM SERVICE` | Never repairable in place — always a removal candidate pending evaluation. |
| `corrosion` in a high-retention zone | `REMOVE FROM SERVICE` | Severe corrosion in a high-retention zone is treated as structurally significant. |
| Other structural findings (`insulation_damage`, `pitting`, `rust`, `discoloration`, `corrosion` elsewhere) | `SUPERVISOR REVIEW` | Requires a human judgment call the generic mapping can't make without severity data. |
| No finding | `PASS` | Routine processing. |

This mapping is intentionally more conservative than the real scoring
engine (which has access to severity indices, baseline match scores, and
zone-aware escalation — see `_overall_result()` in
`baseline_comparison_scoring_service.py`). It exists only to give the
Knowledge Graph Explorer a reasonable illustrative answer when no real
inspection is behind the query; **the real scored outcome from
`explain_inspection()` always takes precedence** for an actual
inspection record.

## Zone assignment note

Both the reasoning chain and the explainability graph use
`app/services/instrument_zones.py::zone_fields()` — the same deterministic
`pilot_zone_assignment` engine used throughout Phases 15–20. This means
the "Inspection Zone" step in the reasoning chain is not a free choice of
words; it's the exact same zone a supervisor would see on the Pre-
Sterilization Command Center or the Pilot Validation Dashboard for the
same instrument/finding combination — the knowledge graph doesn't
introduce a second, inconsistent zone-naming scheme.
