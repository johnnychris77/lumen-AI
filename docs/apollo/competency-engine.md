# Project Apollo — Competency Center

LumenAI OS v4.7, Section 5.

## No parallel competency model

`competency_service.py`'s single `CompetencyEvent` log (table
`competency_events`) already tracked `finding_reviewed`,
`supervisor_correction`, `repeated_error`, and `education_completed`
events before Apollo. `event_type` is an unconstrained `String(30)` column
— there was never a DB-level enum to extend, so adding new event types is
purely additive at the application layer.

Apollo adds four new event types to the *same* log:

| Event type | Recorded by | Notes |
|---|---|---|
| `annual_competency` | `record_annual_competency` | `finding_type` column reused to store the competency area label |
| `procedure_validation` | `record_procedure_validation` | `finding_type` reused to store the procedure name |
| `simulation_passed` / `simulation_failed` | `record_simulation_result` | Outcome is encoded in the event type itself — never a fabricated numeric score |
| `knowledge_contribution` | `record_knowledge_contribution` | `finding_type` reused to store the contribution topic |

`competency_summary` now also returns `annual_competencies`,
`procedure_validations`, `simulations_passed`, `simulations_failed`, and
`knowledge_contributions` counts alongside the pre-existing fields.

## Managing Technicians / Supervisors / Managers

The Competency Center tab composes the pre-existing
`technician_quality_dashboard` (inspection counts, coverage quality,
average AI confidence, supervisor agreement, repeat corrections, training
progress) with the new event-type totals — no second aggregation of the
same underlying events.

## API

```
GET   /api/apollo/competency/summary
POST  /api/apollo/competency/annual                { "technician": "...", "competency_area": "..." }
POST  /api/apollo/competency/procedure-validation   { "technician": "...", "procedure_name": "..." }
POST  /api/apollo/competency/simulation             { "technician": "...", "scenario": "...", "passed": true }
POST  /api/apollo/competency/knowledge-contribution { "technician": "...", "topic": "..." }
```

Every write is audit-logged and updates the same user's real profile —
nothing is scored automatically without an actual recorded event.
