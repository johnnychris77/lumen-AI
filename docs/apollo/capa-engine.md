# Project Apollo — CAPA Engine

LumenAI OS v4.7, Section 2.

## No sixth CAPA store

Before Apollo, this codebase already had:

* `capa_service.py` — the canonical sqlite-backed `capas` table.
* `capa_lifecycle_service.py` (v2.9) — the real
  `open → assigned → in_progress → verified → closed` state machine, added
  as additive columns on the same table.
* `capa_suggestion_service.py` (v1.5) — auto-trigger detection from real
  recurring patterns.
* A legacy `EnterpriseCapa` table and `CAPARecommendation` suggestion queue.

Apollo adds **no new CAPA store**. It extends `capa_suggestion_service.
generate_capa_suggestions` with 5 new detectors the sprint brief names that
didn't already exist — "Repeated Blood Findings" and "Repeated Corrosion"
were already covered by the existing zone/condition-type counters.

## The 5 new detectors

| Trigger | Real signal used |
|---|---|
| Repeat repairs | `RepairRequest.instrument_identity` (from `or_connect.py`) — 3+ repair requests on the same instrument in 90 days |
| Supervisor overrides | `SupervisorReview.agreement == "disagree"` or a non-empty `override_action` — 3+ per reviewer in 90 days |
| AI confidence decline | Reuses `sentinel_ai_health_service._detect_drift` directly — never re-derived |
| Inspection failures | `Inspection.disposition` in `{"REPROCESS", "REMOVE FROM SERVICE"}` — 3+ per instrument type in 90 days |
| Customer complaints | The new `CustomerComplaint` model — 3+ per instrument type in 90 days |

Every detector reuses the same `_REPEAT_THRESHOLD = 3` / `_LOOKBACK_DAYS =
90` constants the pre-existing detectors already used, for consistency.

## Owner / Root Cause / Actions / Verification / Effectiveness Review / Closure

Every CAPA created from a suggestion (via
`POST /api/apollo/capa/suggestions/create`) is materialized through the
existing `capa_suggestion_service.create_capa_from_suggestion` — the human
review step is unchanged. From there, the pre-existing
`capa_lifecycle_service` lifecycle already tracks Owner (`assignee`),
Root-Cause link (`root_cause_assignment_id`), Verification (`verified_by`/
`verified_at`), and Closure (`closed_by`/`closed_at`).

## Customer complaint intake

`CustomerComplaint` (table `apollo_customer_complaints`) is the one
genuinely new store in this section — a complaint intake never existed
before. A complaint can be linked to a CAPA
(`POST /api/apollo/capa/complaints/{id}/link`) or closed independently
(`POST /api/apollo/capa/complaints/{id}/close`). Linking sets
`linked_capa_id` and moves `status` to `linked_to_capa`.

## API

```
GET   /api/apollo/capa/summary
POST  /api/apollo/capa/suggestions/create
POST  /api/apollo/capa/complaints
GET   /api/apollo/capa/complaints
POST  /api/apollo/capa/complaints/{id}/link
POST  /api/apollo/capa/complaints/{id}/close
```

All CAPA/complaint mutations are audit-logged.
