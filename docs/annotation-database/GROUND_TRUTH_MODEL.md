# Ground Truth Model

## The rule

An `Annotation`'s `ground_truth_status` becomes `ACTIVE`
(`app.models.annotation_database.GROUND_TRUTH_ACTIVE`) only via
`annotation_ground_truth_service.promote_to_ground_truth()`, which
requires **one** of:

- Primary Review + independent Secondary Review, with `AnnotationReview.agreement == True`, or
- Clinical Adjudication (`AnnotationReview.resolved_at` set and `resolution` non-empty).

`is_eligible_for_ground_truth()` is the single, explicit gate — there is
no other code path that sets `ground_truth_status = "ACTIVE"`.

## AI predictions are never Ground Truth

`promote_to_ground_truth()` takes an `AnnotationReview` — a real human
review record — as a required argument and never reads `Annotation.model_version`
(the AI-assistance marker) as sufficient justification on its own. An
annotation created directly from an AI observation (`model_version` set)
still requires the same independent human review chain before it can
become Ground Truth.

## Role gate

Only `admin`/`clinical_reviewer` may call `promote_to_ground_truth()`
(`ROLES_MAY_FINALIZE_GROUND_TRUTH`) — enforced both in the service
(defense in depth) and at the route layer
(`POST /api/annotations/{id}/promote-ground-truth`).

## Versioning

Every promotion increments `Annotation.ground_truth_version` — a real,
monotonically increasing counter, never reset — so a specific Ground
Truth version can always be cited (e.g. in a model card or training
manifest) even after a later re-adjudication produces a new version.
