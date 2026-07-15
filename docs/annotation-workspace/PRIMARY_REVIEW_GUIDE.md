# Primary Review Guide

Source: `annotation_review_service.submit_primary()`,
`POST /api/annotations/{id}/review/primary`, frontend
`PrimaryReviewWorkspacePage.tsx` (`/review/primary`).

## Queue

Drawn from `GET /api/reviewer-queues`'s `primary_review_due` bucket
(`reviewer_queue_service.get_queues()`) — the same real, backend-computed
queue every workspace in this sprint reads from. No due date, workload
count, or assignment is invented; an annotation appears here only because
it genuinely has no primary review yet.

## Submitting a review

`label` (one of the 10-category `OBSERVATION_TAXONOMY`), optional
`confidence` (0–1) and `comments`. Role gate: `ROLES_MAY_REVIEW`
(`admin`/`clinical_reviewer`/`spd_manager` — Reviewer role and above;
`operator`/Annotator cannot submit a primary review).

## After submission

The annotation moves to `review_status = LABELED` and appears in the
Secondary (Blind) Review queue. The workspace does not null out the
selected annotation or its context on success — only the form's own
input fields (`label`/`confidence`/`comments`) are cleared, so the
confirmation banner and the item stay visible until the reviewer chooses
to pick the next queue item. This fixes a UX defect found via live
browser testing during this sprint: the entire two-column layout was
previously gated on `queue.length > 0`, so submitting the last queued
item emptied the queue and unmounted the confirmation banner along with
it. The layout is now gated on `queue.length > 0 || selected`.

## Tests

`backend/tests/test_reviewer_queues.py`.
