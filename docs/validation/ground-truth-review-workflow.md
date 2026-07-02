# Ground Truth Review Workflow — Phase 18

## Overview

Every pilot inspection generates an AI prediction. A trained SPD supervisor
then reviews that prediction and records the actual finding, producing a
ground-truth label used for all downstream clinical performance, zone
performance, and safety-queue metrics.

Ground truth is stored in `pilot_validation_cases`
(`app/models/pilot_validation.py`) and reaches that table one of two ways:

1. **Primary path — the existing supervisor-review form.** A supervisor
   submits `POST /inspections/{id}/supervisor-review`
   (`app/routes/ai_clinical_review.py`), the same form already used to
   record AI agreement. That single submission now also builds and
   persists a linked `PilotValidationCase`
   (`build_case_from_supervisor_review` in `pilot_validation_service.py`) —
   the reviewer never fills out a second form. The response includes
   `pilot_validation_case_id` and `ground_truth_label`.
2. **Secondary path — direct case submission.** `POST
   /api/pilot-validation/cases` (`app/routes/pilot_validation.py`), gated
   to `admin` and `spd_manager`, for backfilling historical cohort data or
   cases that don't originate from a live inspection review.

Both paths run through the same server-side label derivation, so the two
are equivalent as far as every downstream metric is concerned.

## What Is Captured Per Inspection

| Field | Description |
|---|---|
| `ai_prediction` | Did the AI flag a positive finding? |
| `ai_confidence` | AI's confidence score for that prediction (0–1). |
| `ai_recommended_disposition` | What the AI's clinical-review layer recommended. |
| `supervisor_finding` | Did the supervisor confirm the finding is actually present? |
| `supervisor_zone_correction` | Corrected instrument zone, if the AI's zone assignment was wrong. |
| `final_disposition` | The disposition the supervisor actually applied (pass / reprocess / quarantine / escalate). |
| `reviewer_rationale` | Free-text rationale — required whenever the supervisor disagrees or overrides. |
| `instrument_family` / `manufacturer` / `model` | Study cohort tracking fields. |
| `anatomy_zone` | The zone under review (see the zone taxonomy in `app/services/pilot_validation_service.py`). |
| `baseline_source` / `has_baseline` | Whether a baseline image was available for comparison. |
| `finding_type` / `severity` | What kind of finding, and how severe. |

## Ground Truth Labels

The system derives one of five labels from `ai_prediction` +
`supervisor_finding` — this derivation always happens server-side
(`derive_ground_truth_label` in `pilot_validation_service.py`) and cannot be
supplied directly by a client:

| AI prediction | Supervisor finding | Label |
|---|---|---|
| Positive | Positive (confirmed) | **True Positive (TP)** |
| Positive | Negative (not actually present) | **False Positive (FP)** |
| Negative | Positive (missed by AI) | **False Negative (FN)** |
| Negative | Negative (confirmed) | **True Negative (TN)** |
| Either missing | — | **Inconclusive** |

False negatives on a *critical* finding type (blood, tissue, organic
residue, crack, missing component) are additionally flagged
`is_critical_finding = true` and routed to the safety review queue's
`critical_missed_findings` bucket.

## Review Steps

1. **AI review generated.** The inspection's AI prediction, confidence, and
   recommended disposition are recorded automatically at inference time.
2. **Supervisor reviews the case.** The supervisor examines the instrument
   (and image) directly, independent of the AI's stated confidence, and
   determines whether the finding is genuinely present
   (`finding_correct` on the supervisor-review form).
3. **Supervisor records zone correction, if needed.** If the AI's zone
   assignment doesn't match where the finding actually is, the supervisor
   sets `zone_correct: false` and supplies `corrected_zone`. The zone name
   is normalized onto the Phase 18 dashboard taxonomy
   (`normalize_zone` in `pilot_validation_service.py`) — e.g. the
   instrument-zone vocabulary's singular "hinge" becomes "hinges".
4. **Supervisor sets the final disposition** and a rationale — required
   whenever the disposition disagrees with the AI's recommendation
   (`override_rate` is computed from this).
5. **One submission creates both records.** `POST
   /inspections/{id}/supervisor-review` persists the `SupervisorReview` and
   the derived `PilotValidationCase` in the same transaction. The
   ground-truth label and `is_critical_finding` flag are computed
   immediately from the inspection's AI output and the supervisor's
   `finding_correct` answer; the case becomes part of every subsequent
   metrics computation right away.
6. **Audit events logged.** Every submission creates both a
   `supervisor_ai_review` audit event and a `pilot_validation_case_reviewed`
   audit event (`compliance_flag=true`), satisfying the "every
   intelligence-sharing action creates an audit event" requirement for
   this data.

## Data Quality Expectations

- A case with a missing `anatomy_zone` (or a zone outside the taxonomy) is
  surfaced in the safety queue's `missing_required_zones` bucket — it is not
  silently dropped from metrics, but it is flagged for follow-up.
- A case without a linked baseline is surfaced in `missing_baseline_cases`.
- Reviewer rationale is expected (not enforced at the DB layer, but
  reviewed in the safety queue) whenever the label is FP, FN, or an override
  occurred.
