# Smart Inspection Queue

`GET /api/inspection-work-queue` · frontend route `/inspection-work-queue`

## What it is

A single, ranked view of every inspection that hasn't reached a terminal
workflow state (`Completed` or `Cancelled`), answering the question SPD asks
every shift: **"what should we inspect next?"**

Nothing in the queue is a new analysis — each item is a rollup of signals
that already exist elsewhere in the platform:

| Signal | Source |
|---|---|
| Readiness score/status | `readiness_engine.compute_readiness()` (v1.6) |
| Disposition recommendation | `disposition_engine.recommend_disposition()` (v1.6) |
| Risk tier | `risk_stratification_service.stratify_risk()` (v1.6) |
| Priority score/tier | `prioritization_engine.compute_priority()` (Deliverable 2) |
| Current workflow state | `workflow_state_service.current_state()` (Deliverable 4) |
| Assigned technician | `workflow_state_service.latest_assignment()` (Deliverable 3) |

## Response shape

```json
{
  "pending_inspections": [ ... ],
  "high_risk_inspections": [ ... ],
  "or_priority_instruments": [ ... ],
  "vendor_trays": [ ... ],
  "loaner_instruments": [ ... ],
  "repeat_inspections": [ ... ],
  "supervisor_reviews": [ ... ],
  "repair_holds": [ ... ],
  "total_pending": 12,
  "human_review_required": true
}
```

Each queue item includes: `instrument_type`, `procedure_priority`,
`workflow_state`, `risk_tier`, `priority_score`/`priority_tier` (with the
`priority_reasons` that produced the score), `disposition`, `coverage_pct`,
`minutes_waiting`, `assigned_technician`, and the `is_vendor_tray` /
`is_loaner_instrument` / `has_repeat_findings` flags used to place the item
into its buckets.

`pending_inspections` is the master list (sorted by `priority_score`
descending); the other keys are the same items filtered into the specific
buckets SPD asks for. An item can appear in more than one bucket (e.g. a
high-risk vendor-tray instrument in a repair hold).

## Honesty notes

- An inspection only leaves the queue once it reaches `Completed` or
  `Cancelled` — there is no "hide after N days" behavior that could mask a
  stalled inspection.
- `procedure_priority` and `is_loaner_instrument` are `null`/`false` unless
  actually declared at intake (`POST /api/inspections`) — never inferred or
  defaulted to "routine".
- `assigned_technician` is `null` until a supervisor explicitly assigns one
  (Deliverable 3) — never guessed from who submitted the inspection.
