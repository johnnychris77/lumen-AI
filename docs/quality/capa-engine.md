# CAPA Recommendation Engine + Lifecycle

Codename: Project Guardian · LumenAI Quality v2.9

## No parallel CAPA system

`docs/quality/capa-integration.md` already establishes "no parallel CAPA
system" as policy for this codebase. The real CAPA store is
`capa_service.py`'s raw-sqlite `capas` table — predating any SQLAlchemy
model for CAPA. This sprint extends that table additively
(`capa_lifecycle_service.ensure_lifecycle_columns` — idempotent
`ALTER TABLE`, new nullable columns only) rather than introducing a second
CAPA model.

New columns: `tenant_id`, `lifecycle_status`, `recommendation_type`,
`assignee`, `linked_event_id`, `linked_inspection_id`,
`root_cause_assignment_id`, `verified_by`/`verified_at`,
`closed_by`/`closed_at`.

## Recommendation types

`CAPARecommendation` suggests one of eight typed actions, derived from the
event's SPD taxonomy category (or, better, from an approved RCA draft's
category):

| Category | Typical recommendations |
|---|---|
| organic_residue | education, competency_review |
| instrument_condition | equipment_evaluation, repair_referral |
| assembly | process_audit, observation |
| packaging | process_audit |
| sterilization_indicators | equipment_evaluation, follow_up_inspection |
| unknown | observation |

A recommendation is only a suggestion (`status: suggested`) until a human
either **accepts** it — which materializes a real CAPA via
`capa_lifecycle_service.create_capa_with_recommendation` — or **dismisses**
it. Nothing is ever auto-created, mirroring the existing
`capa_suggestion_service.py`'s "suggestions never auto-create CAPAs" rule.

## Lifecycle

The existing `capas.status` free string only ever saw `open`/`closed`/
`cancelled`/`in_progress` ad hoc, with no enforced state machine. This
sprint adds the real one, on the new `lifecycle_status` column:

```
Open -> Assigned -> In Progress -> Verified -> Closed
```

`capa_lifecycle_service.advance_lifecycle` validates every transition
against an explicit table — `open` can go to `assigned`, `in_progress`, or
directly to `closed`; `verified` can only go to `closed`; `closed` is
terminal. An invalid transition (e.g. `open` straight to `verified`)
returns 422 with the valid next states listed.
