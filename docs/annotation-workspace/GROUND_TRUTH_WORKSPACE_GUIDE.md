# Ground Truth Workspace Guide

Source: `annotation_ground_truth_service.promote_to_ground_truth()` /
`is_eligible_for_ground_truth()` (pre-existing, unchanged),
`POST /api/annotations/{id}/promote-ground-truth`, frontend
`GroundTruthWorkspacePage.tsx` (`/ground-truth`).

## Three independent cards, three independent empty states

| Card | Source | Empty state |
|---|---|---|
| Eligible for Promotion | `reviewer-queues`'s `ground_truth_eligible` bucket | "No annotations are currently eligible." |
| Awaiting Adjudication | `reviewer-queues`'s `adjudication_due` bucket, links to `/review/adjudication` | "No disagreements are pending." |
| Active Ground Truth | `GET /api/annotations?ground_truth_status=ACTIVE` | "No Ground Truth annotations yet." |

Each card fetches and renders independently — one card's empty collection
never hides another's content or its own empty message, avoiding the
same conditional-rendering-on-emptiness defect fixed in the review
workspaces (`PRIMARY_REVIEW_GUIDE.md`).

## Promotion requirements (enforced by the pre-existing service, not this sprint)

- Two independent reviews must have agreed, or a disagreement must have
  been adjudicated.
- An AI-model-originated annotation (non-empty `model_version`) can never
  be promoted without a completed human review —
  `test_ai_assisted_annotation_cannot_be_promoted_without_human_review`
  confirms a `409` in this case, not a silent override.
- Promotion is `admin`/`clinical_reviewer` only.

## Ground Truth immutability

Once `ground_truth_status = ACTIVE`, the annotation's history is
append-only (`AnnotationVersion` snapshots) — see
`docs/annotation-database/GROUND_TRUTH_MODEL.md`, unchanged by this
sprint.

## Tests

`backend/tests/test_reviewer_queues.py`,
`backend/tests/test_project_canvas_checklist.py::test_ai_assisted_annotation_cannot_be_promoted_without_human_review`.
