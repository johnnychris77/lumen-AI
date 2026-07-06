# Pilot Site Configuration — v1.9

`GET/PUT /api/pilot-deployment/site-config` (GET: any authenticated role;
PUT: admin only)

## What it is

One row per tenant (`PilotSiteConfig`) holding the small set of
structured, machine-read settings the pilot's own guardrails and the
Pilot Data Collection Dashboard read directly:

| Field | Meaning | Default |
|---|---|---|
| `facility_name` | The pilot site's facility name | `""` |
| `department` | The pilot site's department | `""` |
| `enabled_instrument_families` | Which of `instrument_anatomy.py`'s families this site actually processes | `[]` (all families remain usable; this is an informational filter, not a hard gate) |
| `required_inspection_zones` | Site-declared required zones, supplementing (never replacing) each instrument family's own required-image list in `instrument_anatomy.py` | `[]` |
| `baseline_required` | Whether an approved baseline must exist before an inspection can be scored complete | `true` |
| `minimum_coverage_pct` | Coverage percent below which an inspection is flagged incomplete by the Data Quality Guardrails | `75` |
| `supervisor_review_threshold_score` | Advisory threshold surfaced to supervisors — not a hard gate on top of the existing disposition engine | `70` |

A site always has a config — `get_or_create_config()` returns
conservative defaults on first access rather than leaving "no config"
ambiguous about which rules apply.

## Why this is separate from `OrganizationStandard` (v1.8)

`OrganizationStandard` is a list of free-text policy documents a
supervisor authors and titles (inspection standards, photography
standards, competency requirements, etc.) — narrative guidance for humans
to read. `PilotSiteConfig` is the handful of *structured* values other
code actually reads (the guardrails service, the data-collection
dashboard). Both supplement, never replace, manufacturer IFUs or the AI's
own readiness/disposition/risk engines — neither overrides a code path in
the scoring engine.

## Relationship to per-instrument-family requirements

`instrument_anatomy.py` already defines each family's own `required_images`
and `min_images` (e.g. how many views a Kerrison rongeur needs) — this is
the authoritative, per-family requirement used by
`guided_capture.coverage_readiness()` at inspection time.
`PilotSiteConfig.required_inspection_zones` is an **additional**,
site-level declaration (e.g. "this site additionally wants X documented
for audit purposes") — it does not replace or reduce the per-family
requirement.
