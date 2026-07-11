# Project Vulcan — Repair Effectiveness Intelligence

LumenAI AI Specialist, Section 5.

## Composing real repair + finding evidence

`vulcan_repair_effectiveness_service.classify_repair_outcome` composes the
real `RepairRequest` row (`app/models/or_connect.py` — repair date, vendor,
type, status, return dates, coarse `failure_category`) with the real
`InspectionFinding` rows on the inspection that triggered the repair and any
inspections after the instrument's return.

`RepairRequest` has no zone column of its own. The affected anatomy zone is
derived from the pre-repair inspection's most severe finding — never
fabricated.

## Outcome classification

| Outcome | Meaning |
|---|---|
| `effective` | no recurrence in the same zone after return |
| `partially_effective` | recurrence at lower severity than before |
| `failure_recurred` | recurrence at the same/greater severity |
| `new_defect_detected` | a previously-unseen finding type appears in the same zone |
| `unable_to_determine` | repair not yet returned, or no post-repair inspection exists yet |

`time_to_recurrence_days` is computed from real timestamps (return date to
first recurring inspection), never estimated.

## No unsupported vendor claims

Outcomes describe what the inspection evidence shows — recurrence, new
defect, or no recurrence — never a statement that a vendor performed a bad
repair.

## API

```
GET /api/vulcan/repair-effectiveness?instrument_identity=...
```
