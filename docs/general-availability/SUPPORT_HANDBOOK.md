# Support Handbook — LumenAI Version 1.0 (Pilot Program)

**Status:** consolidates the real support-structure documentation already
built (`docs/commercial-readiness/SUPPORT_OPERATIONS_MANUAL.md`), honestly
marking what exists as process/design vs. real tooling.

## Support tiers and escalation (documented, not yet tool-backed)

A real L1/L2/L3/Clinical escalation structure and P0-P3 severity/SLA table
is defined in `docs/commercial-readiness/SUPPORT_OPERATIONS_MANUAL.md`,
sourced from `docs/regulatory/software-lifecycle-readiness.md` §8.1:

| Severity | Definition | Target response |
|---|---|---|
| P0 | Safety-relevant incident or complete outage | See the manual's SLA table |
| P1 | Major feature broken, no safe workaround | See the manual's SLA table |
| P2 | Degraded functionality, workaround exists | See the manual's SLA table |
| P3 | Minor issue, cosmetic, or enhancement request | See the manual's SLA table |

**Known gap**: no dedicated ticketing/case-management tooling exists yet.
For the first pilot, use a clearly designated, monitored channel (email
alias or shared inbox) as the single intake point until real tooling is
selected.

## Safety events — always P0/P1, always reviewed

Every safety event reported through `POST /api/advisory-pilot/safety-events`
requires explicit human review before it can be closed
(`advisory_safety_service.review_event()`) — there is no auto-close path.
Treat any `unsafe_recommendation`, `near_miss`, or `critical_incident`
event type as at minimum P1 until reviewed.

## Incident response

**Known gap**: no security or clinical incident-response runbook exists
yet (`GO_LIVE_CHECKLIST.md` item #5). Author one before the pilot begins —
at minimum: who is notified, within what timeframe, and what containment
steps apply, for both a security incident and a clinical safety incident.

## On-call

**Known gap**: no rotation exists. Define at minimum an informal on-call
owner for the pilot's duration.

## What technicians/supervisors/quality staff should know

- Every AI recommendation is clearly labeled as such and requires human
  confirmation — see `docs/advisory-pilot/ADVISORY_MODE_GUIDE.md`.
- Structured feedback can be submitted at any time via
  `POST /api/advisory-pilot/feedback` — this directly feeds the pilot's
  success evaluation.
- Training materials: `docs/demo-program/TRAINING_GUIDE.md`,
  `docs/pilot/pilot-user-training-guide.md`.

## Escalation contacts

To be populated per pilot facility at contract signing — this document
intentionally does not fabricate a contact list, since no real pilot
contract exists yet at the time of this report.
