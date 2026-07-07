# Anatomy Profile Service

Given an instrument's type (and optionally name/manufacturer/model), resolve
its anatomy: family, zones, required image views, high-risk zones, per-zone
descriptions, contamination/condition risks, and manual-check guidance. This
is the "step 2" service LumenAI Inspect v1.1 requires before AI analysis.

## Source of truth

`backend/app/services/instrument_anatomy.py`

- `INSTRUMENT_ANATOMY` — per-family zone definitions (`_zone(name, category,
  risk, retention, contamination, condition)`), `match` keyword list for
  free-text classification, `required_images`, `recommended_image_angles`,
  `min_images`, `manual_steps`.
- `resolve_family(instrument_type)` — free-text → family key. Falls back to
  `"default"` (a generic SPD profile) rather than guessing.
- `get_anatomy(instrument_type)` — full anatomy for a resolved family.
- `anatomy_profile(instrument_type, manufacturer=None, model=None,
  instrument_name=None)` — the full contract: considers every identity hint
  available, and when nothing matches returns `instrument_family: "unknown"`,
  `profile_found: False`, and a `warning` recommending supervisor review.
  Nothing is fabricated as a specific match.
- `list_anatomy_families()` — summary of every declared family (v1.1
  addition), for the Anatomy Library's browse view.

Families: 112 as of v1.10 (see `docs/instrument-knowledge/v1.10-instrument-knowledge-expansion.md`
for the full specialty breakdown), plus `default` (generic fallback). The
original 8 — rigid scope, flexible endoscope, drill bit, Kerrison/rongeur,
scissors, needle holder, laparoscopic, general forceps — are unchanged.
Flexible endoscopes are declared before rigid scopes in the match table so
endoscope-specific keywords resolve first (a rigid scope's generic
"scope"/"endoscope" match would otherwise swallow them); the v1.10 expansion
families are declared before all 8 originals for the same reason, using
distinctive multi-word match phrases so none of the originals' resolution
behavior changes.

## API

- `GET /api/instrument-anatomy` — all anatomy families (v1.1 addition).
- `GET /api/instrument-anatomy/{instrument_type}?manufacturer=&model=&instrument_name=`
  — resolved profile for one instrument.

## Frontend

`/anatomy-library` (`frontend/src/pages/AnatomyLibraryPage.tsx`) — a lookup
form (resolve any instrument type/manufacturer/model combination) plus a
browsable list of every declared anatomy family.

## Unknown instruments

When no family matches, the generic `default` profile is returned along with
`warning: "Instrument anatomy profile not found. Supervisor review
recommended."` — the caller (New Inspection workflow, AI analysis) surfaces
this so a human confirms the instrument identity rather than the system
silently guessing.
