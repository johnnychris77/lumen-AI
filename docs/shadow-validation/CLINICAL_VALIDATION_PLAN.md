# Clinical Validation Plan

**Status:** New this pass (Shadow). **Code:** `backend/app/models/pilot.py`
(`PilotStatus`, extended), `backend/app/services/pilot_service.py`
(extended), `backend/app/routes/shadow_validation.py`.

## Objective

Generate trustworthy, real-world evidence about the Genesis
production-candidate model's performance before it is ever used in an
advisory capacity — via one or more pilot facilities running Shadow Mode
against live inspections.

## Pilot site configuration (§2)

`PilotStatus` (pre-existing since the P14 pilot-conversion gate, table
`pilot_status`) is extended additively with the fields §2 requires that
did not already exist on it:

| Field | Status |
|---|---|
| `tenant_id`, `facility_id` | Pre-existing |
| `pilot_start_date`, `pilot_end_date` | Pre-existing |
| `organization` | New this pass |
| `department` | New this pass |
| `clinical_lead` | New this pass |
| `technical_lead` | New this pass |
| `quality_lead` | New this pass |
| `validation_coordinator` | New this pass |

`app.services.pilot_service.start_pilot()` gained matching optional
keyword arguments (default `""`) — every pre-existing caller that omits
them keeps the original 90-day, blank-lead behavior unchanged.

`PilotSiteConfig` (v1.9, table `pilot_site_configs`) is a **different**,
pre-existing entity — the machine-read guardrail settings (coverage
thresholds, required zones) a facility's own inspection workflow reads.
It is not duplicated or modified by this pass; a pilot facility typically
has both a `PilotStatus` row (this program's roles/dates) and a
`PilotSiteConfig` row (workflow guardrails).

## API

- `POST /api/shadow-validation/pilot-sites` — register a facility's pilot
  program (organization, department, the four named leads, agreed KPIs,
  end date).
- `GET /api/shadow-validation/pilot-sites/{facility_id}` — read it back.

## Process

1. Register the pilot site (organization, facility, department, leads).
2. Run the inspection workflow exactly as today — Shadow Mode observes,
   never intervenes (`SHADOW_MODE_PROTOCOL.md`).
3. Collect ground truth on every inspection (`GROUND_TRUTH_GUIDE.md`).
4. Review disagreements as they queue (`ERROR_REVIEW_PROCESS.md`).
5. Monitor drift continuously (`MODEL_DRIFT_MONITORING.md`).
6. Convene the Clinical Review Board periodically
   (`docs/shadow-validation/` — see the promotion policy below).
7. Generate weekly/monthly reports (`VALIDATION_REPORT_TEMPLATE.md`).
8. Evaluate readiness against `READINESS_CRITERIA.md` before any
   promotion beyond Candidate.

## Definition of done

A prospective shadow-mode validation using real-world inspection
workflows has completed, generating sufficient evidence to support an
**informed decision** about advancing to supervised advisory use. Human
inspectors remain the sole decision-makers throughout. No production
claims are made beyond the validated scope and results.
