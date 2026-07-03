# Instrument Knowledge Library

LumenAI Inspect v1.1 — before any contamination/damage analysis runs, the
platform first resolves what instrument it is looking at. The Instrument
Knowledge Library is the structured, data-driven knowledge base behind that
step.

## Source of truth

`backend/app/services/instrument_family_profiles.py` — `INSTRUMENT_FAMILY_PROFILES`

Ten instrument families, each with:

| Field | Meaning |
|---|---|
| `display_name` | Human-readable family name |
| `typical_anatomy` | Live anatomy zones for the family (resolved from `instrument_anatomy.py` — never a duplicated copy) |
| `high_risk_zones` | Zones with elevated inherent/retention risk |
| `typical_contamination` | Contamination types typically found on this family |
| `typical_damage` | Damage patterns typically found on this family |
| `typical_repair_issues` | Common repair/rework reasons |
| `inspection_priorities` | Zones to prioritize during visual inspection |
| `cleaning_priorities` | Manual-check guidance for reprocessing staff |
| `supervisor_focus_areas` | What a supervisor should specifically verify |
| `anatomy_family_note` | Present only when a family honestly borrows another family's anatomy taxonomy rather than fabricating zones that were never defined (e.g. Cannulated Instruments, Orthopedic Instruments, Micro Instruments) |

Covered families: Rigid Scope, Flexible Endoscope, Kerrison, Needle Holder,
Scissors, Drill Bit, Laparoscopic Instruments, Cannulated Instruments,
Orthopedic Instruments, Micro Instruments — a superset of the eight families
in the v1.1 spec (rigid scope, flexible endoscope, drill bit, Kerrison/rongeur,
scissors, needle holder, laparoscopic instrument, general forceps — the
general-forceps anatomy family also has its own dedicated zone taxonomy, see
`anatomy-library.md`).

## API

- `GET /api/instrument-families` — all family profiles.
- `GET /api/instrument-families/{family_key}` — one family profile (404 with
  the list of known keys if unrecognized).

## Frontend

`/instrument-library` (`frontend/src/pages/InstrumentLibraryPage.tsx`) —
browsable cards, one per family, expandable to the full profile.

## Design decision: no fabricated coverage

Three families (Cannulated Instruments, Orthopedic Instruments, Micro
Instruments) do not yet have a dedicated anatomy-zone split — they borrow the
closest existing anatomy family and say so via `anatomy_family_note`, rather
than inventing zones that were never defined. Extend by adding a new anatomy
family in `instrument_anatomy.py` and pointing `anatomy_family_key` at it.
