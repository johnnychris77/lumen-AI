# Instrument Anatomy Registry

LumenAI Inspect v2.0 — "Project Anatomy." The registry is the single source
of truth every anatomy-aware component reads from: `INSTRUMENT_ANATOMY` in
`backend/app/services/instrument_anatomy.py`.

## What's in the registry

112 real instrument families (v1.10) plus the `default` generic fallback.
Each family declares:

- **Anatomy hierarchy** — `category` (specialty grouping, e.g. "orthopedic
  biter") and the family's `zones` list.
- **Zone hierarchy** — each zone has a `zone_name` and a `zone_category`
  (one of `cutting_working_surface`, `rotary_orthopedic`, `lumen_scope`,
  `mechanical`, `handle_external` — see `zone-intelligence.md`).
- **Risk hierarchy** — each zone carries `zone_risk_level`
  (low/medium/high/critical) and `retention_risk` (low/medium/high). See
  `zone-risk-matrix.md` for how these roll up into a platform-wide matrix.
- **Inspection guidance** — `required_images`, `recommended_image_angles`,
  `min_images`, and `manual_steps` per family; `required_lighting` and
  `recommended_angle` per zone_category (see `inspection-zone-guidance.md`).
- **Cleaning guidance** — resolved per zone name via
  `app/services/cleaning_knowledge.py` (`get_cleaning_knowledge()`).
- **Expected failure modes** — each zone's `contamination_risks` /
  `condition_risks`, now zone-category-specific rather than one generic
  list (v2.0 — see `zone-intelligence.md`).

## Entry points

- `resolve_family(instrument_type)` — free-text → family key (`"default"`
  when nothing matches; never guessed).
- `get_anatomy(instrument_type)` — full zone list + guidance for a family.
- `anatomy_profile(instrument_type, manufacturer=None, model=None,
  instrument_name=None)` — the full contract used by
  `GET /api/instrument-anatomy/{instrument_type}`.
- `list_anatomy_families()` — every declared family, for the Anatomy
  Library's browse view (`GET /api/instrument-anatomy`).

## Related registries this hierarchy feeds

- `app/services/instrument_family_profiles.py` — 10 knowledge profiles
  (typical contamination/damage/repair issues, inspection/cleaning
  priorities, supervisor focus areas) that each point at a real anatomy
  family via `anatomy_family_key` — no more borrowed anatomy as of v1.10.
- `app/services/knowledge_graph_service.py` — the SPD Clinical Knowledge
  Graph traverses this same registry (`reasoning_chain()`,
  `explain_inspection()`, and the `instrument_family` explorer category).
- `app/services/zone_intelligence.py` (v2.0) — the Anatomy Zone Engine,
  Zone Risk Matrix, and Dynamic Inspection Guidance all read this registry
  live; nothing is duplicated into a separate v2.0-only dataset.
