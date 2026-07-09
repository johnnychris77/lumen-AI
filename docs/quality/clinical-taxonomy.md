# SPD Quality Taxonomy

Codename: Project Guardian · LumenAI Quality v2.9

## A governed, versioned taxonomy — deliberately separate from existing finding vocabularies

Before this sprint, `finding_type` was a free string populated from several
different, unreconciled in-code vocabularies (`contamination_agent.py`'s
`CONTAMINATION_FINDING_TYPES`, `damage_agent.py`'s `DAMAGE_FINDING_TYPES`,
`clinical_mentor.py`'s `FINDING_EDUCATION` keys, `analytics.py`'s own
subset). None of these overlapping sets have ever been versioned. Rather
than unify or rename those (which AI agents and existing dashboards
actively depend on), `QualityTaxonomyTerm` establishes one canonical,
governed taxonomy scoped specifically to the Quality Event Engine's
classification output.

## The six categories

| Category | Terms |
|---|---|
| `organic_residue` | blood, bone, tissue, protein, debris |
| `instrument_condition` | rust, corrosion, pitting, crack, wear |
| `assembly` | missing_instrument, wrong_instrument, missing_component |
| `packaging` | wet_tray, wrapper_tear, filter_failure, missing_lock |
| `sterilization_indicators` | failed_indicator, missing_indicator |
| `unknown` | requires_supervisor_classification |

## Versioned and configurable

`QualityTaxonomyTerm.version` records the taxonomy version a term was added
under (`TAXONOMY_VERSION` in `app/models/quality_guardian.py`, currently
`1`). `DEFAULT_TAXONOMY` seeds every tenant's table on first use
(`quality_taxonomy_service.ensure_default_taxonomy`); tenants can add
further terms at runtime via `POST /api/quality-guardian/taxonomy` without
a code deploy — the "configurable" half of the requirement. Bumping
`TAXONOMY_VERSION` in a future release and re-seeding is how the taxonomy
itself would be versioned forward.

## Endpoints

- `GET /api/quality-guardian/taxonomy` — full taxonomy by category
- `POST /api/quality-guardian/taxonomy` — add a custom term (leadership roles)
