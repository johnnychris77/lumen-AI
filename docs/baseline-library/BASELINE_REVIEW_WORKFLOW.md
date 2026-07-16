# Baseline Review Workflow — Project Atlas Sprint 1

Implements mission Sections 4 and 5: the governed lifecycle a baseline
image moves through, and the real review record required before it can
become the current, comparison-eligible reference.

## Lifecycle states (`BASELINE_IMAGE_STATES`)

`DRAFT → PENDING_REVIEW → APPROVED → ACTIVE`, with `SUSPENDED`,
`SUPERSEDED`, `REJECTED`, and `ARCHIVED` as terminal or side states.

## Valid transitions (`VALID_BASELINE_IMAGE_TRANSITIONS`)

```
DRAFT           -> {PENDING_REVIEW, ARCHIVED}
PENDING_REVIEW  -> {APPROVED, REJECTED, ARCHIVED}
APPROVED        -> {ACTIVE, ARCHIVED}
ACTIVE          -> {SUSPENDED, SUPERSEDED, ARCHIVED}
SUSPENDED       -> {ACTIVE, SUPERSEDED, ARCHIVED}
SUPERSEDED      -> {ARCHIVED}
REJECTED        -> {ARCHIVED}
ARCHIVED        -> {}  (terminal)
```

Every transition is validated by `_require_transition()` in
`baseline_image_library_service.py`, which raises `InvalidTransitionError`
(mapped to HTTP 409) for anything not in this table. Because `ACTIVE` is
reachable only from `APPROVED`, and `APPROVED` is reachable only from
`PENDING_REVIEW` via `review_baseline_image(decision="approve")`, "only
ACTIVE approved baseline images may influence live comparison" (Section 4)
is a structural property of the state machine, not a convention a caller
could bypass.

## The review record (Section 5)

`review_baseline_image()` requires `reviewer_role` to be one of
`ROLES_MAY_REVIEW_BASELINE_IMAGE = {admin, clinical_reviewer, spd_manager}`
and the link to currently be `PENDING_REVIEW`. It writes a
`BaselineImageReview` row capturing: reviewer, reviewer role, decision
(approve/reject), rationale (required, non-empty), limitations, source
verification notes, anatomy-compatibility confirmation, image-quality
assessment, review date, and next review date. On approval, the link's
`approved_by`/`approved_at` are set and its state moves to `APPROVED`; on
rejection, to `REJECTED`.

Multiple reviews may exist per link (a rejected image resubmitted after
correction gets a new review row) — the link's own `lifecycle_status`
always reflects the *latest* decision, while every prior review remains
queryable via the audit history and (indirectly) via
`baseline_image_reviews` rows.

## The activation gate (Section 4's "activation requires")

`activation_gate_failures()` checks, and `activate_baseline_image()`
refuses to proceed (raising `ActivationGateError` with the full list of
missing items, mapped to HTTP 422) unless **all** of the following hold:

1. The linked LCID entry (`DatasetRegistryEntry`) still resolves.
2. `retained_image_id` is set on that entry — image registration is
   complete.
3. `usage_rights` is documented (non-empty) on that entry.
4. `phi_verification == "verified"` on that entry.
5. `image_quality` is not `Reject`, `Poor`, or blank.
6. Instrument identity is sufficiently resolved — either the Digital Twin
   is tracked (`not is_untracked_twin(...)`), or the link itself carries a
   real `manufacturer` and `model_name`.
7. `anatomy_zone` is documented on the link.
8. `inspection_view` is documented on the link.
9. A `BaselineImageReview` with `decision="approve"` exists for this link.
10. `image_sha256` is stored (non-empty).
11. `baseline_version` is assigned (non-empty).

Only `admin`, `clinical_reviewer`, or `spd_manager` may call `activate`,
`suspend`, `archive`, or `supersede` (`ROLES_MAY_ACTIVATE_BASELINE_IMAGE`)
— the same role set that may review. An Administrator can manage lifecycle
transitions but cannot bypass any of the eleven evidence checks above; there
is no administrative override path in the service layer.

## Suspension, archival, and supersession

- **Suspend**: `ACTIVE → SUSPENDED` with a required `reason`. A suspended
  image can be reactivated (`SUSPENDED → ACTIVE`) directly — re-running the
  full activation gate — without needing a new review.
- **Archive**: available from any non-terminal state; a pure "no longer
  relevant" marker, distinct from rejection.
- **Supersede**: `supersede_baseline_image()` requires the *new* link to
  already be `APPROVED` (not merely `DRAFT`) before it can take over. The
  old link moves to `SUPERSEDED` (with `superseded_at`/`superseded_by` set)
  and the new link moves to `ACTIVE` (with `supersedes_link_id` pointing
  back). The old row's data is never edited or deleted — "superseded
  baseline remains historically visible" (Section 16 checklist item) holds
  because supersession is implemented as two state changes on two distinct
  rows, never an in-place edit.

## Frontend

`BaselineImageDetailPage.tsx` (`/baselines/library/:baselineId`) surfaces
every lifecycle action available to the current user's role and the
link's current state, and the review form requires a non-empty rationale
before the Approve/Reject buttons are enabled. `BaselineReviewWorkspacePage.tsx`
(`/baselines/review`) lists everything currently `PENDING_REVIEW` for
reviewers to work through.
