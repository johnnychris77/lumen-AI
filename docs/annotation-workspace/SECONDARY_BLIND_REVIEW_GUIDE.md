# Secondary (Blind) Review Guide

Source: `app/services/annotation_blind_review_service.py`
(`get_blind_secondary_view()`),
`GET /api/annotations/{id}/review/secondary/blind-view`,
`POST /api/annotations/{id}/review/secondary`, frontend
`SecondaryReviewWorkspacePage.tsx` (`/review/secondary`).

## Blindness is backend-enforced, not a client-side hide

`get_blind_secondary_view()` returns only the image, safe metadata
(instrument family, manufacturer, image quality), annotation
instructions, and an `eligible_to_submit_secondary` flag with a
`blocked_reason` when not eligible. It never reads or serializes any
`AnnotationReview` field — `primary_label`, `primary_confidence`,
`primary_comments`, `agreement`, and `primary_reviewer` are absent from
the response entirely, not merely omitted by the frontend. A reviewer who
opens browser devtools and inspects the raw network response still cannot
see the primary reviewer's classification before submitting their own.

`annotation_review_service.submit_secondary()` separately blocks the same
person who submitted the primary review from also submitting the
secondary review for that annotation (`ReviewerCannotSelfSecondaryError`).

## Agreement / disagreement

On submission, the service computes `agreement` by comparing the two
independent labels. Agreement moves the annotation toward Ground Truth
eligibility (`GROUND_TRUTH_WORKSPACE_GUIDE.md`); disagreement routes it to
the Disagreement Queue (`/review/disagreements`) for adjudication
(`ADJUDICATION_WORKSPACE_GUIDE.md`).

## UX fix applied this sprint

Same defect class as `PRIMARY_REVIEW_GUIDE.md`: the queue+detail layout
is gated on `queue.length > 0 || selected` (not `queue.length > 0` alone),
and on success the `<form>` is hidden (`result?.type !== "success"`)
while the confirmation banner, image, and metadata remain visible above
it — verified via a live Playwright drive that the banner persists after
submitting the last queued item.

## Tests

`backend/tests/test_review_workspace.py` — asserts the blind-view
response never contains primary-review content even after a primary
review has been submitted, and that the primary reviewer is blocked from
self-secondary.
