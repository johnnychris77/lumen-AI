# Zone Assignment Engine (pilot)

Source of truth: `backend/app/services/instrument_zones.py`
(`resolve_zones`, `zone_for_finding`, `zone_fields`, `ZONE_INFO`,
`HIGH_RETENTION_ZONES`).

## What it is

Given an instrument family and a finding, the engine assigns a probable
**instrument zone**, its **risk**, a **reason**, and a **recommended manual
check**. Contamination findings route to the instrument's high-retention
contamination zone; condition findings route to the condition zone.

Inputs (pilot):
- instrument family / type
- tagged inspected zones (checklist) when available
- filename / view hints when available
- baseline metadata

Output per finding:
- `instrument_zone`
- `zone_risk`
- `zone_reason`
- `recommended_manual_check`

## This is NOT computer vision

The assignment is **`pilot_zone_assignment`** — deterministic from instrument
type, not pixel-level localization. It is honestly labeled as such throughout
the code and UI. We do not pretend a region was visually segmented.

Example resolutions:

| Instrument | Contamination zone | Condition zone |
|---|---|---|
| drill bit | drill-bit flute | threaded region |
| flexible endoscope | biopsy channel | lens edge |
| rigid scope | o-ring area | lens edge |
| forceps / needle holder | serrations | box lock |
| scissors | hinge | cutting edge |
| kerrison / rongeur | box lock | jaws |

## Retention escalation

Findings in `HIGH_RETENTION_ZONES` (serrations, box lock, hinge, flutes,
channels, o-ring area, insulation edge, …) escalate contamination risk relative
to the same finding on a flat external surface — because residual soil is harder
to remove there.

## Future true-CV migration

A trained segmentation model replaces `resolve_zones` with per-pixel zone
localization while keeping the same output schema. Supervisor zone corrections
(`SupervisorReview.zone_correct` / `corrected_zone`) accumulate as the labeled
dataset. Until then, the tagged-view checklist supplies ground-truth zone
context.
