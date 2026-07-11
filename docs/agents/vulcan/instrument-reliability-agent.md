# Project Vulcan — Instrument Reliability Agent

LumenAI AI Specialist, Mission & Section 1.

## What Vulcan does

Vulcan investigates recurring instrument defects, condition changes, repair
patterns, and premature failures. It determines what is failing, where the
failure occurs, whether it is recurring, how the condition is progressing,
whether prior repairs were effective, and whether the issue is
cleaning-related, maintenance-related, use-related, design-related, or
undetermined.

Vulcan supports pre-sterilization inspection and asset-quality decisions. It
does not certify instrument safety independently — supervisor, clinical
engineering, repair vendor, and manufacturer review remain available where
appropriate.

## Deterministic, not an autonomous LLM

Vulcan is a deterministic Python orchestrator
(`vulcan_reliability_agent_service.run_reliability_assessment`) composing
real evidence from existing data. There is no LLM or embedding API call
anywhere in Vulcan — the same invariant every prior sprint in this codebase
protects.

## Architecture position

```
Instrument Intelligence -> Anatomy Intelligence -> Zone Intelligence ->
Inspection Findings -> Digital Twin History -> Repair History ->
Failure Analysis -> Reliability Assessment -> Recommended Disposition ->
Human Validation -> Knowledge Capture
```

## What is reused vs. genuinely new

Vulcan composes real, pre-existing data rather than inventing a parallel
instrument-history store:

- **Finding history** — `InspectionFinding` (v1.5) already logs one row per
  actionable finding; this *is* the progression/anatomy-zone history Vulcan
  analyzes.
- **Repair history** — `RepairRequest` (`app/models/or_connect.py`) already
  tracks vendor, repair type, status, return dates, and a coarse
  `failure_category`. Vulcan's granular taxonomy maps onto it for
  repair-effectiveness correlation.
- **Instrument identity/anatomy** — `Inspection.instrument_udi`/
  `instrument_barcode` (the real cross-inspection identity key, via the
  established `_instrument_identity` helper) and `instrument_anatomy.py`'s
  real anatomy-zone taxonomy.
- **Digital Twin / baseline versions** — referenced by version string only
  in the audit trail, never copied.

Genuinely new: three tables (`VulcanReliabilityAssessment`,
`VulcanRepairEffectivenessAssessment`, `VulcanFeedback`) and twelve service
modules (`vulcan_*_service.py`).

## Responsibilities (Section 1)

- monitor recurring defects
- compare current and prior inspections
- identify repeated anatomy-zone failures
- evaluate repair effectiveness
- identify worsening corrosion or wear
- detect repeat removal-from-service events
- identify instruments with abnormal failure frequency
- recommend repair, monitoring, manufacturer evaluation, or retirement

Every conclusion carries evidence (`evidence_json`) and a confidence label
(`confidence`).

## API

```
POST /api/vulcan/assess
GET  /api/vulcan/assessments/{id}
```

See `docs/agents/vulcan/reliability-score.md` for the scoring rubric and
`docs/agents/vulcan/instrument-forensics-workspace.md` for the full
investigative UI.
