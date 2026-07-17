# Clinical Pilot Protocol — Phase 1 (Initial Real-World Pilot)

Builds on `docs/advisory-pilot/PILOT_PROTOCOL.md` (advisory-mode
governance, promotion gates) and `docs/pilot/pilot-launch-runbook.md`.
This protocol narrows Phase 1 to the mission's objectives: demonstrate
safe advisory operation under real clinical workflows with complete
governance, traceability, and human oversight.

## Standing rules (non-negotiable)

* LumenAI is **advisory only**. No clinical decision is made solely by
  AI; no patient-care decision depends exclusively on LumenAI output.
* The AI channel operates **observe-only** in Phase 1: the registered
  model is Experimental (synthetic-data-only); its output is disclosed
  as such, recorded for observation, and never gates a workflow step.
* No performance claims during or after Phase 1 — observation only.
  Any metric without adequate evidence is reported `insufficient_data`.
* Every intelligence-sharing action creates an audit event; hospital
  identities in any cross-facility view remain anonymized; correlation
  outputs carry `human_review_required: true` and speak only of
  "potential association".

## Scope

One SPD department at one pilot site (`PILOT_SITE_SELECTION.md`),
approved instrument families and anatomy zones recorded before launch,
daily inspection cap agreed with the clinical sponsor, fixed pilot
duration (recommend 4–6 weeks). Scope changes require sponsor sign-off
and a protocol amendment — never silent expansion.

## Workflow under test (with timing capture)

Instrument arrival → technician scan/select → borescope capture →
upload (Canvas ingestion, LCID assigned) → baseline retrieval (Atlas
resolution hierarchy) → AI inference (advisory, disclosed) → advisory
display → technician decision (accept / modify / reject, reason
captured) → supervisor review where policy requires → annotation +
independent review → Ground Truth where collected → Digital Twin update.

Each step is timed on the `PILOT_OBSERVATION_FORMS.md` timing form;
results aggregate into `WORKFLOW_TIMING_REPORT.md` (template until real
data exists).

## Success metrics (Section 10) — definitions and sources

| Metric | Source | Note |
|---|---|---|
| Successful uploads / upload attempts | Canvas ingestion audit events | |
| System availability | `/health`, `/ready`, GPAE deep checks | |
| Average inference time | inference records | |
| Baseline retrieval rate | comparator `resolution_scope` outcomes incl. `no_approved_baseline` | |
| Annotation completion | annotation lifecycle states | |
| Ground Truth completion | GT version records | |
| Technician / supervisor satisfaction | feedback instruments (`USER_FEEDBACK_PLAN.md`) | |
| Workflow completion rate | inspection state machine terminal states | |
| System reliability | error/safety event log | |

Targets are set with the clinical sponsor **before** launch and recorded
in the site-selection record; they are not adjusted after seeing data
without a documented amendment.

## Safety monitoring and stopping

Record every item in mission Section 7 on the safety form. Immediate
containment triggers (suspend AI advisory display, manual workflow
continues): image/result identity mismatch, contradiction attempts,
model checksum failure, audit-write failure, any suspected cross-tenant
exposure, or any SEV-1 event. Restart requires the clinical sponsor and
engineering sign-off, recorded in the audit trail.

## Exit criteria (Section 11)

Phase 1 completes only when all of the following hold with real
evidence: stable platform through the pilot window; zero unresolved
critical safety events; all collected data governed (LCID, versioned
annotations/GT, audit-complete); reliable image persistence (zero lost
or hash-mismatched images); a documented workflow assessment; lessons
learned recorded; and a pilot completion report **approved by the
clinical sponsor**. Templates for the last three exist in this
directory and remain templates until the pilot produces the evidence.
