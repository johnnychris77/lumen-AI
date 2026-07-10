# Dynamic Inspection Guidance

`dynamic_inspection_guidance(instrument_type, zone_name, *,
coverage_status=None)` in `app/services/zone_intelligence.py`, exposed at
`GET /api/anatomy/inspection-zone-guidance/{instrument_type}/{zone_name}`.

## What it returns

Everything the capture UI needs to display for the zone currently being
inspected:

| Field | Source |
|---|---|
| `current_zone` | the requested zone name |
| `risk_level` | the zone's real `zone_risk_level` |
| `expected_findings` | zone-category-specific contamination + condition findings (see `zone-intelligence.md`) |
| `inspection_tips` | the family's `manual_steps` that mention this zone by name, falling back to the full list |
| `required_lighting` | per-`zone_category` lighting guidance (see below) |
| `recommended_angle` | per-`zone_category` viewing-angle guidance |
| `coverage_status` | passed through from the caller (e.g. the Inspection Coverage Engine), defaults to `"not_assessed"` when not supplied — never fabricated as "captured" |

## Required lighting / recommended angle, by zone_category

| zone_category | Required lighting | Recommended angle |
|---|---|---|
| `cutting_working_surface` | Raking side light with magnification | Edge-on, blade/jaw flat to the light source |
| `rotary_orthopedic` | High-intensity magnified light | Flute/thread close-up, tip end-on |
| `lumen_scope` | Borescope or internal channel illumination | Distal end-on, channel/port opening |
| `mechanical` | Raking light with the joint actuated fully open | Pivot open, hinge/ratchet/box-lock exposed |
| `handle_external` | Standard ambient light | Overall view, side profile |

This is real, general SPD visual-inspection practice (lumens need internal
illumination because surface light can't reach a channel; a pivot needs to
be open and raking-lit to reveal residue in the recess) rather than one
generic "inspect closely" tip repeated for every zone.

## Coverage status is never fabricated

`coverage_status` is a pass-through parameter, not something
`dynamic_inspection_guidance()` computes itself — the caller (typically the
capture flow, which already knows the real coverage state from
`app/services/inspection_coverage.py`) supplies it. When omitted, the
function honestly reports `"not_assessed"` rather than guessing.

## 404 behavior

Both this endpoint and the underlying Anatomy Zone Engine return `404` when
`zone_name` isn't actually a declared zone for the instrument's resolved
family, rather than silently returning a generic/wrong chain — see
`TestDynamicInspectionGuidance::test_unknown_zone_returns_none` in
`backend/tests/test_v2_0_anatomy_aware_clinical_intelligence.py`.
