# Adjudication Workspace Guide

Source: `annotation_review_service.adjudicate()`,
`POST /api/annotations/{id}/review/adjudicate`,
`GET /api/annotations/{id}/review` (added this sprint to
`app/routes/annotation_database.py`), frontend
`AdjudicationWorkspacePage.tsx` (`/review/adjudication`).

## Who may adjudicate

`ROLES_MAY_FINALIZE_GROUND_TRUTH` — `admin`/`clinical_reviewer` only. The
frontend route itself is also gated to these two roles (a plain Reviewer
who navigates here directly sees a "Not authorized" screen, backed by the
same backend 403 if they call the API directly).

## Why the review-detail endpoint is narrowly gated

`GET /annotations/{id}/review` (used here to show both independent
reviews side by side) is deliberately gated to
`ROLES_MAY_FINALIZE_GROUND_TRUTH`, not the broader `ROLES_MAY_REVIEW` —
if a plain Reviewer could call it, they could read the primary review
before submitting their own secondary review, defeating
`SECONDARY_BLIND_REVIEW_GUIDE.md`'s blindness guarantee. Only the two
adjudicator roles, who by definition act after both reviews already
exist, can see this endpoint.

## Requirements

`adjudicate()` only applies to a review whose `agreement is False`
(`AdjudicationNotRequiredError` otherwise — adjudication cannot be used to
skip the two-reviewer step). Both a non-empty `resolution` and a
non-empty `reason` are required (`AdjudicationReasonRequiredError`,
surfaced as `422`) — an adjudication with no documented rationale is
never accepted.

## After adjudication

The annotation becomes eligible for Ground Truth promotion
(`GROUND_TRUTH_WORKSPACE_GUIDE.md`); adjudicating does not, by itself,
set `ground_truth_status = ACTIVE` — an explicit promotion step is still
required.

## UX fix applied this sprint

Same layout-gating and result-banner-persistence fix as the primary/
secondary workspaces (`queue.length > 0 || selected`, form hidden on
success rather than the whole panel unmounting).

## Tests

`backend/tests/test_reviewer_queues.py` (full disagreement flow),
`backend/tests/test_project_canvas_checklist.py::test_adjudication_without_reason_rejected`.
