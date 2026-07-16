# Annotation Guide

**Status:** New this pass. **Code:**
`backend/app/models/dataset_governance.py` (`AnnotationEvent`,
`DoubleBlindReview`, `ImageQualityAssessment`),
`backend/app/services/ml/annotation_workflow.py`,
`backend/app/services/ml/double_blind_review.py`,
`backend/app/services/ml/image_quality.py`.
**API:** `POST /api/dataset-registry/images/{id}/annotation-transition`,
`GET .../annotation-history`, `POST .../double-blind/{primary,independent,adjudicate}`,
`POST .../quality-assessment`.
**Tests:** `backend/tests/test_dataset_registry.py::TestAnnotationWorkflow`,
`::TestDoubleBlindReview`, `::TestImageQualityAssessment`.

This is a formal, audited annotation lifecycle — distinct from
`app.models.retained_image.RetainedImage.label_status`'s simpler 4-value
string (`unlabeled → labeled → in_review → gold|rejected`), which is left
untouched and still governs that model's own consumers. This lifecycle is
the richer, 7-state one this program's brief specifically requires.

## The 7 states

```
UNLABELED → LABELED → SECOND_REVIEW → ADJUDICATED → APPROVED
                    ↘ DISAGREEMENT ↗
(ARCHIVED reachable from any non-terminal state)
```

| State | Meaning |
|---|---|
| `UNLABELED` | No annotation yet. |
| `LABELED` | A first reviewer has applied a label. |
| `SECOND_REVIEW` | An independent second reviewer is reviewing. |
| `DISAGREEMENT` | The two reviewers' labels do not match. |
| `ADJUDICATED` | A third reviewer (the adjudicator) resolved a disagreement. |
| `APPROVED` | Final, gold-standard label — eligible for training (subject to the other exclusion filters in `DATASET_REGISTRY.md`). |
| `ARCHIVED` | Retired — excluded from training regardless of any other flag. |

Every transition is validated against a fixed table (`app.services.ml.
annotation_workflow.transition()`); an out-of-order move (e.g. `UNLABELED`
straight to `APPROVED`) is rejected with `InvalidTransitionError` /
HTTP `409`, never silently accepted. Every event records `reviewer`,
`timestamp`, `confidence`, `comments`, and a `changes_json` field for
structured before/after diffs — append-only, mirroring
`app.services.workflow_state_service`'s inspection-workflow pattern, so the
current state is always the latest event's `to_state`, never a mutated
column.

## Double-blind review (Section 4)

`app.services.ml.double_blind_review` records:

- **Primary reviewer** + label + confidence + timestamp.
- **Independent reviewer** + label + confidence + timestamp — must be a
  different person from the primary reviewer (`ReviewerCannotSelfIndependentError`
  otherwise). Blind by construction: the service never surfaces the primary
  label to the caller submitting the independent one.
- **Agreement** — computed automatically once both labels are in
  (`primary_label == independent_label`).
- **Adjudicator** + **resolution** + **reason** — required only when the two
  reviewers disagreed (`AdjudicationNotRequiredError` if called on an
  agreement); a blank reason is rejected (`ReasonRequiredError`).

This is distinct from the pre-existing critical-class two-reviewer *count*
gate in `app.routes.ml_images` (which just checks "two labels exist" before
allowing adjudication) — this module is the formal record of exactly which
two people said what and how a disagreement was resolved.

## Image quality assessment (Section 5)

`app.services.ml.image_quality.assess_image_bytes()` computes, from **real
pixel data** (Pillow — no new dependency):

| Check | How | Flag |
|---|---|---|
| Blur | Edge-energy variance (`ImageFilter.FIND_EDGES` + stddev) below threshold | `blur_flag` |
| Focus | Same signal, a looser threshold | `focus_flag` |
| Exposure / lighting | Mean brightness outside 40–215 (0–255 scale) | `exposure_flag` / `lighting_flag` |
| Cropping | Width/height below 200×200, or aspect ratio outside 0.4–2.5 | `cropping_flag` |
| Visibility | Composite of blur + exposure (disclosed as a proxy, not object-level occlusion detection — no such detector exists in this codebase) | `visibility_flag` |

Overall quality: `Excellent` (no flags) → `Good` (1 flag) → `Marginal` (2) →
`Poor` (3+) → `Reject` (cropping/resolution failure, or the bytes are not a
decodable image at all — never guessed). **`Reject` images are excluded
from training** (`app.services.ml.image_quality.excluded_from_training()`,
enforced in the dataset builder — see `DATASET_REGISTRY.md`).

This replaces two previously-honest-but-placeholder mechanisms with real
computation: `app.services.veritas_image_quality_service` (derived quality
from `has_image`/`ai_confidence`, not pixels) and
`app.services.ml.feature_store`'s `image_blur_score`/`lighting_quality_score`
(previously always `null`, now populated with the same real Pillow
computation when `image_bytes` is supplied).
