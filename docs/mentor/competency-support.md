# Competency Support (v1.4)

## What it tracks
`backend/app/models/competency_event.py` is an append-only event log; each row
is one of:

- `finding_reviewed` — a supervisor reviewed one of this technician's
  inspections.
- `supervisor_correction` — the supervisor disagreed, partially agreed, or
  overrode the AI on that inspection, tagged with the `finding_type` involved.
- `repeated_error` — the same technician has now been corrected on the same
  `finding_type` at least twice; logged automatically alongside the
  correction that crosses the threshold.
- `education_completed` — the technician marked a knowledge-library article
  as read (`POST /api/mentor/education/{finding_type}/complete`).

## Where it's recorded
`app/routes/ai_clinical_review.py`'s existing `POST
/inspections/{id}/supervisor-review` endpoint (the ML ground-truth capture
path) also calls `competency_service.record_finding_reviewed` /
`record_supervisor_correction` in the same transaction — competency tracking
piggybacks on a review that was already happening, rather than requiring a
second workflow.

## Technician attribution
`Inspection.technician` (added in v1.4, nullable) is set from the request
actor at creation time (`POST /api/inspections`). Older inspections created
before this field existed have `technician = null` and are simply excluded
from competency aggregation — never backfilled with a guess.

## Summary shape
`GET /api/mentor/competency/{technician}`:
```
{
  "technician": "jane@hospital.org",
  "findings_reviewed": 12,
  "supervisor_corrections": 3,
  "repeated_errors": {"blood": 2},
  "education_completed": ["blood", "crack"],
  "training_progress_pct": 33,
  "has_activity": true
}
```
`training_progress_pct` is `null` (not `0`) when there have been no supervisor
corrections yet — there is nothing to score, and the engine never fabricates
a number for a technician with no recorded activity.

## Access control
A technician may only view their own summary; `admin`/`spd_manager` may view
anyone's.
