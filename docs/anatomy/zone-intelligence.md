# Zone Intelligence — the Anatomy Zone Engine

`backend/app/services/zone_intelligence.py`. Formalizes the chain v2.0
requires before any clinical recommendation:

```
Instrument -> Anatomy -> Inspection Zone -> Risk Level -> Typical Findings
-> Recommended Inspection Method
```

## `zone_engine(instrument_type, zone_name)`

Given an instrument type and one of its declared anatomy zones, returns the
full chain: resolved `instrument_family`, `zone_category`,
`zone_risk_level`, `retention_risk`, `typical_contamination_findings`,
`typical_condition_findings`, `cleaning_method`, `required_lighting`, and
`recommended_angle`. Returns `None` — never a fabricated chain — when
`zone_name` isn't actually declared for that instrument's resolved family.

Exposed at `GET /api/anatomy/zone-engine/{instrument_type}/{zone_name}`.

## Zone-Specific Finding Models

Before v2.0, every zone in `INSTRUMENT_ANATOMY` defaulted to the same two
generic lists (`_CONTAM`/`_COND`) regardless of what kind of zone it was —
a rigid-scope o-ring and a drill-bit flute reasoned identically. v2.0 adds
`TYPICAL_FINDINGS_BY_CATEGORY` in `instrument_anatomy.py`, keyed by the five
`zone_category` values every declared zone already uses:

| zone_category | typical contamination | typical condition |
|---|---|---|
| `cutting_working_surface` | blood, bone, tissue, debris | corrosion, pitting, dulling, nicked edge |
| `rotary_orthopedic` | bone, metal shavings, retained debris | corrosion, wear, dulled cutting surface |
| `lumen_scope` | blood, organic residue, debris | discoloration, crack, damaged seal, pitting |
| `mechanical` | blood, tissue, debris | corrosion, wear, loose pivot, fatigued spring |
| `handle_external` | blood, debris | insulation damage, discoloration, cosmetic wear |

`_zone()` now uses this table as the default for `contamination_risks` /
`condition_risks` — an explicit `contamination=`/`condition=` argument on a
call to `_zone()` still overrides it for a genuinely atypical zone. This is
why a Kerrison serration (`cutting_working_surface`) and a rigid-scope
o-ring (`lumen_scope`) now carry genuinely different expected findings
end-to-end, matching the mission's own example.

## Bridging the two zone vocabularies

The pilot scoring engine (`app/services/instrument_zones.py`,
`zone_fields()`) uses an older, smaller zone taxonomy (~18 zone names) built
before the v1.1/v1.10 per-family anatomy registry existed. Rather than
maintaining two independent finding-vocabulary systems,
`_LEGACY_ZONE_TO_CATEGORY` in `zone_intelligence.py` maps every legacy zone
name onto the same five `zone_category` buckets, and
`typical_findings_for_legacy_zone(zone_name)` looks up the same
`TYPICAL_FINDINGS_BY_CATEGORY` table. `baseline_comparison_scoring_service
.analyze_inspection()` calls this for every predicted finding, so the real
AI reasoning engine's output — not just the Anatomy Library's read-only
view — reasons per zone category (see `clinical-anatomy-model.md`).

## `zone_risk_for_name(zone_name)`

Best-effort risk tier for a bare zone name from either vocabulary — checks
the legacy taxonomy's own `risk` field first, then scans the anatomy
registry for the first declared zone with that name. Returns `None` only
if the name isn't declared anywhere. Used by Learning Dataset v2 to attach
a real `zone_risk` to each row without re-deriving it from scratch.
