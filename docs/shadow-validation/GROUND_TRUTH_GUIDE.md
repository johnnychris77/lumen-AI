# Ground Truth Guide

**Status:** New this pass (Shadow). **Code:**
`backend/app/models/shadow_validation.py` (`ShadowGroundTruth`),
`backend/app/services/ml/shadow_ground_truth.py`.

## Ground truth is the final human-reviewed outcome — never the AI's

`shadow_ground_truth.final_finding(row)` returns the adjudicated finding
when one has been recorded, otherwise the supervisor's finding — **never**
the AI's own prediction, and never the technician's finding alone once a
supervisor has reviewed it.

## Why a new table, distinct from `SupervisorReview`

`SupervisorReview` (Phase 18) already captures a single reviewer's
AI-agreement feedback (`ai_finding_present`/`supervisor_finding_present`/
`ground_truth`) for the deployed placeholder scoring engine. It has no
field for the **original technician finding** captured independently of
any review, no adjudicator identity, and only one review timestamp.
`ShadowGroundTruth` fills exactly that gap for the Shadow Mode program,
without duplicating or modifying `SupervisorReview`.

## The three-stage chain

| Stage | Fields | Recorded by |
|---|---|---|
| Technician | `technician_finding`, `technician_name`, `technician_reviewed_at` | `record_technician_finding()` |
| Supervisor | `supervisor_finding`, `supervisor_name`, `supervisor_reviewed_at` | `record_supervisor_finding()` |
| Adjudication (optional) | `final_adjudicated_finding`, `adjudicator_name`, `adjudicated_at`, `reason_for_correction`, `supporting_evidence` | `record_adjudication()` |

Adjudication is only needed when the final finding differs from the
supervisor's — `reason_for_correction` and `supporting_evidence` exist
specifically to make that correction traceable and reviewable, never a
silent overwrite.

`is_locked(row)` — ground truth is locked once a supervisor finding
exists; this is the same real signal `shadow_mode.reveal_if_finalized()`
gates on via the inspection's own workflow state, not a second source of
truth.

## Reviewer identities and timestamps

Every stage records a real name (`technician_name`/`supervisor_name`/
`adjudicator_name`) and a real timestamp — never inferred, never
defaulted to "system." A ground-truth record with a blank name at a given
stage means that stage genuinely has not happened yet.

## API

- `POST /api/shadow-validation/ground-truth` — record the technician
  finding.
- `PATCH /api/shadow-validation/ground-truth/{id}/supervisor-finding` —
  record the supervisor's finding.
- `PATCH /api/shadow-validation/ground-truth/{id}/adjudication` — record
  an adjudicated correction, with reason and evidence.
- `GET /api/shadow-validation/ground-truth` — the full registry.

## Inter-reviewer agreement

`shadow_validation_metrics.inter_reviewer_agreement()` compares the
technician's and supervisor's findings directly — a real signal of how
often the two independent human reviewers agreed, before any adjudication
— surfaced in `GET /api/shadow-validation/validation-metrics`.
