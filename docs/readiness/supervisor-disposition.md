# Supervisor Disposition Workspace (v1.6)

## What a supervisor may do
`POST /api/inspections/{id}/disposition-action` records one of:
`approve`, `modify`, `escalate`, `reclean`, `repair`,
`remove_from_service`, `manufacturer_review`.

## Reason required for overrides
A `reason` is required for every action except `approve` — enforced by
`disposition_workspace_service.submit_disposition_action()`
(`ReasonRequiredError`, surfaced as HTTP 422), not just a frontend nicety.
Approving the AI's recommendation as-is needs no justification; changing it
does.

## Separate from the ML-ground-truth supervisor-review endpoint
`DispositionOverride` (this feature) is deliberately a different table from
`SupervisorReview` (the existing `/inspections/{id}/supervisor-review`
endpoint, which captures AI-agreement for model-performance tracking) and
from `MentorCoachingReview` (v1.4's coaching-quality tracking). Each table
answers a different question:
- `SupervisorReview` — did the AI get it right? (ML ground truth)
- `MentorCoachingReview` — was the AI's coaching helpful? (education quality)
- `DispositionOverride` — what should happen to this instrument next, and
  why? (operational decision)

## History
`GET /api/inspections/{id}/disposition-actions` returns every action taken
on an inspection, newest first — a full audit trail of who changed what
disposition and why.
