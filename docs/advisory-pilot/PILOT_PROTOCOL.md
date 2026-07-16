# Pilot Protocol

**Status:** New this pass (Advisor). **Code:** `backend/app/models/pilot.py`
(`PilotStatus`, extended), `backend/app/services/pilot_service.py`
(extended), `backend/app/routes/advisory_pilot.py`.

## Pilot governance (§2)

`PilotStatus` (pre-existing since P14, extended by Shadow with
organization/department/clinical_lead/technical_lead/quality_lead/
validation_coordinator) gains the remaining §2 fields this pass:

| Field | Status |
|---|---|
| `pilot_sponsor` | New this pass |
| `product_owner` | New this pass |
| `engineering_lead` | New this pass |
| `success_criteria` (structured narrative) | New this pass — distinct from the pre-existing `agreed_kpis` JSON, which is purely numeric target/actual tracking |
| `pilot_duration_days` | New this pass — the planned/target duration, kept independently of the actual `pilot_start_date`/`pilot_end_date` (e.g. when a pilot is extended) |

`pilot_service.start_pilot()` gained matching optional keyword arguments
with backward-compatible defaults — every pre-existing caller is
unaffected.

## API

`POST /api/advisory-pilot/governance` registers a facility's advisory
pilot: organization, facilities, department, pilot sponsor, clinical
lead, quality lead, product owner, engineering lead, success criteria,
and pilot duration.

## Process

1. Register pilot governance (this doc).
2. Enable Advisory Mode for the facility (`ADVISORY_MODE_GUIDE.md`) — the
   candidate model's recommendation becomes visible to technicians.
3. Log every interaction (§4) and collect structured user feedback (§7,
   `USER_FEEDBACK_PLAN.md`).
4. Monitor workflow impact (§5) and clinical performance (§6) —
   `GET /api/advisory-pilot/workflow-impact`,
   `GET /api/advisory-pilot/clinical-performance`.
5. Track safety events continuously (§8) — every concern requires review.
6. Review the pilot dashboard (§9, `PILOT_DASHBOARD_GUIDE.md`) and
   evaluate success metrics (§10, `SUCCESS_METRICS.md`) on a regular
   cadence.
7. Convene the Clinical Review Board (§11) on a scheduled basis, reusing
   Shadow's `ClinicalReviewBoardSession`
   (`app.services.ml.shadow_clinical_review_board`) — now additionally
   carrying a `pilot_decision` field (`continue`/`expand`/`pause`/
   `terminate`), distinct from the `approved` field Shadow already uses
   for the Validated Candidate promotion gate. The same review session
   can carry both: e.g. approved for promotion purposes while the board
   separately decides whether the pilot itself continues.
8. Evaluate the Pilot -> Production promotion gate (§13,
   `PILOT_FINAL_REPORT.md`) only once every gate item is satisfied.

## Definition of done

LumenAI has successfully completed a supervised advisory pilot. AI
recommendations are visible and explainable. Human reviewers retain full
decision-making authority throughout. Pilot outcomes demonstrate
measurable operational and clinical value, providing evidence for
broader production deployment — but broader deployment itself requires
passing the separate Pilot -> Production gate (`PILOT_FINAL_REPORT.md`).
