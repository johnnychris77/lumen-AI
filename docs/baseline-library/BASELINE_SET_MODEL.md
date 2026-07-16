# Baseline Set Model — Project Atlas Sprint 1

Implements mission Section 6 ("Multi-Image Baseline Set"). A `BaselineSet`
groups compatible `BaselineImageLink` rows so a single governed reference
can represent "known-good" across multiple images, rather than depending on
one photo to represent an entire instrument.

## What a set is (and is not)

A `BaselineSet` is a scope declaration plus a membership list — it does not
store or duplicate any image data itself. Every member is an existing
`BaselineImageLink` row (`BaselineSetMember.baseline_image_link_id`).

A set groups images that share:

- one **manufacturer** and **model** (or, for family-level sets, one
  **instrument family**),
- one **anatomy zone**,
- one **approved view protocol** and **orientation protocol**,
- one **version**.

Images with different anatomy zones, views, or orientations belong to
*different* sets (or different members flagged in the same baseline entry
but not the same set) — a set is never used to paper over a compatibility
mismatch; `BaselineCompatibilityContract` checks (see
`BASELINE_COMPATIBILITY_CONTRACT.md`) are evaluated per-image, not
short-circuited by set membership.

## Fields

See `BASELINE_IMAGE_SCHEMA.md` → `baseline_sets` / `baseline_set_members`
for the full column list. Notably:

- `active: bool` — a set can be governed (`lifecycle_status`) independently
  of whether it is the currently active version for its scope; only one
  set per (manufacturer, model, anatomy_zone) scope is expected to be
  `active=True` at a time, though this is a governance convention enforced
  by reviewers today, not yet a DB constraint.
- `supersedes_set_id` — a version change creates a new set row rather than
  editing the old one in place, mirroring the same "old row marked
  superseded, never edited" pattern used for individual `BaselineImageLink`
  rows (Section 4).

## API surface

- `POST /api/baseline-library/sets` — create a set and attach initial
  members (`baseline_image_link_ids`). Requires `_REVIEW_ROLES` (`admin`,
  `spd_manager`, `clinical_reviewer`) — creating a governed grouping is a
  review-level action, not an operator action.
- `GET /api/baseline-library/sets/{set_id}` — returns the set plus its
  current member link IDs (queried live from `baseline_set_members`, not
  cached on the set row).

## Frontend

`/baselines/sets/:baselineSetId` (`BaselineSetDetailPage.tsx`) displays the
set's governance scope and its member baseline images, each linking back to
`/baselines/library/:baselineId` for the individual image's full viewer.

## Relationship to `BaselineImageLink` lifecycle

A `BaselineSet` does not gate an individual image's `lifecycle_status` —
each `BaselineImageLink` still independently passes through
DRAFT → PENDING_REVIEW → APPROVED → ACTIVE (or SUSPENDED/SUPERSEDED/
REJECTED/ARCHIVED) per `BASELINE_REVIEW_WORKFLOW.md`. A set is a
*grouping* of already-independently-governed images, never a shortcut that
activates images by association.
