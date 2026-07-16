# Adjudication Guide

## When adjudication applies

Only when `AnnotationReview.agreement is False` — a real, computed
disagreement between the primary and independent secondary reviewer.
`annotation_review_service.adjudicate()` raises
`AdjudicationNotRequiredError` if called on a review that agreed or was
never completed; adjudication cannot be used to bypass the two-reviewer
step.

## Who may adjudicate

`admin`/`clinical_reviewer` only (`ROLES_MAY_FINALIZE_GROUND_TRUTH`) —
enforced in the service and at the route
(`POST /annotations/{id}/review/adjudicate`).

## What's required

A non-empty `reason` (`AdjudicationReasonRequiredError` otherwise) and a
`resolution` — the adjudicator's final determination. Both are recorded
verbatim on `AnnotationReview.adjudication_reason`/`.resolution`, plus
`resolved_at` and `adjudicator`, and logged as an
`annotation_adjudicated` audit event.

## After adjudication

The annotation becomes eligible for Ground Truth promotion via the
"Clinical Adjudication" path in `GROUND_TRUTH_MODEL.md` — a Clinical
Reviewer/Administrator still must explicitly call
`promote_to_ground_truth()`; adjudication alone does not set
`ground_truth_status = ACTIVE`.
