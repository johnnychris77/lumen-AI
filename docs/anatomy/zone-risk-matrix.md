# Zone Risk Matrix

`zone_risk_matrix()` in `app/services/zone_intelligence.py`, exposed at
`GET /api/anatomy/zone-risk-matrix`.

## What "configurable" means here

The v2.0 spec asks for a configurable risk matrix bucketing zones into
Critical / High / Medium / Low. Rather than hand-maintaining a second,
static example list that would drift out of sync with the anatomy registry
the moment a new family is added, the matrix is **computed live** from the
real `zone_risk_level` every declared zone in `INSTRUMENT_ANATOMY` already
carries — the "configuration" lives in the anatomy data itself. Adding a
new instrument family (or changing an existing zone's risk level)
automatically updates the matrix; nothing needs to be hand-edited in two
places.

```python
def zone_risk_matrix() -> dict[str, list[str]]:
    matrix = {"critical": set(), "high": set(), "medium": set(), "low": set()}
    for defn in INSTRUMENT_ANATOMY.values():
        for zone in defn["zones"]:
            tier = zone["zone_risk_level"] if zone["zone_risk_level"] in matrix else "medium"
            matrix[tier].add(zone["zone_name"])
    return {tier: sorted(names) for tier, names in matrix.items()}
```

## Representative output (v1.10 anatomy registry, 112 families)

| Tier | Example zones |
|---|---|
| Critical | lumens, suction/biopsy channels, drill flutes, o-ring areas (when declared critical), reaming heads, sealing jaws |
| High | serrations, jaws, hinges, ratchets, box locks, threaded regions, insulation edges |
| Medium | cutting edges, shafts, connectors, lens edges |
| Low | handles, cosmetic surfaces, eyepieces |

(Exact counts and membership shift as families are added — call the
endpoint or the service function directly rather than trusting this table
to stay current; see `test_v2_0_anatomy_aware_clinical_intelligence
.py::TestZoneRiskMatrix` for the executable contract.)

## Relationship to the older per-zone `ZONE_INFO` risk field

`app/services/instrument_zones.py` already carried a `risk` field per zone
in its own smaller taxonomy (used by the pilot scoring engine). The v2.0
matrix bucketing is the anatomy-registry-wide generalization of that same
idea — `zone_risk_for_name()` (see `zone-intelligence.md`) checks
`ZONE_INFO` first so the two stay consistent for any zone name that exists
in both vocabularies.
