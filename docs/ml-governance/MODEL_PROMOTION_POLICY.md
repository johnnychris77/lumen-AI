# Model Promotion Policy

**Status:** New this pass (Genesis). **Code:**
`backend/app/services/ml/candidate_promotion.py`.
**API:** `GET/PATCH/POST /api/model-pipeline/models/{id}/candidate-*`.
**Tests:** `backend/tests/test_candidate_model_training.py::TestPromotionRules`.

## Two ladders, two purposes — not one replacing the other

This program introduces a **second** promotion ladder, deliberately kept
separate from the pre-existing `app.services.ml.deployment_gates` ladder:

| Ladder | Governs | Stages |
|---|---|---|
| `deployment_gates` (pre-existing, unchanged) | Whether a model may drive/advise a clinical recommendation at all | experimental → pilot → validated → deprecated |
| `candidate_promotion` (new this pass) | Where a model sits in its own training → validation → deployment lifecycle | Experimental → Candidate → Validated Candidate → Pilot → Production |

The pre-existing `POST /api/model-pipeline/models/{id}/promote` endpoint
and its tests are **completely unaffected** by this addition — the two
ladders are tracked on separate `ModelRegistryEntry` columns
(`approval_status` vs. `candidate_stage`) and evaluated by separate
functions.

## The 8-item checklist (Section 11)

A model CANNOT advance beyond `Candidate` unless every item below is true:

| Item | How it's checked |
|---|---|
| `dataset_frozen` | The `DatasetVersion` referenced by `dataset_version_id` has `frozen == True` |
| `annotation_complete` | Every `DatasetRegistryEntry` for that dataset version is in a terminal annotation state (`APPROVED` or `ARCHIVED`) — none left `UNLABELED`/`LABELED`/`SECOND_REVIEW`/`DISAGREEMENT`/`ADJUDICATED` |
| `evaluation_complete` | `evaluation_metrics` is non-empty |
| `model_card_generated` | `model_card_markdown` is non-empty |
| `registry_updated` | Trivially true once the row exists |
| `reproducible_training_confirmed` | Human-recorded boolean — set only after independently re-running training with the same config and confirming identical results (see `TRAINING_CONFIGURATION.md`) |
| `error_analysis_reviewed` | Human-recorded boolean — set only after a reviewer has examined the ranked failure modes (`ERROR_ANALYSIS.md`) |
| `governance_review_completed` | Human-recorded boolean — the clinical/governance sign-off |

`GET /api/model-pipeline/models/{id}/candidate-checklist` is a read-only
preview of this exact checklist against a model's current state.
`PATCH /api/model-pipeline/models/{id}/candidate-flags` records the three
human-judgment booleans (plus `reviewer`, `clinical_review_status`,
`deployment_status`) — never defaulted true.

## Promotion rules

- Advance **one stage at a time** — `Experimental → Candidate` is the only
  automatic transition (set by `run_full_candidate_pipeline()` itself when
  training succeeds); every subsequent stage requires
  `POST /api/model-pipeline/models/{id}/candidate-promotion` with an
  explicit `target_stage` and a recorded approver.
- **Never auto-promoted** — `evaluate_candidate_promotion()` always returns
  the unmet checklist; the route only writes the new stage when `allowed`
  is `True`.
- **No skipping** — `Candidate → Pilot` directly is rejected; must pass
  through `Validated Candidate` first.

## Definition of Done for this program

Reaching `Candidate` (with a complete checklist) means: the model is
reproducible, fully traceable, scientifically documented, and eligible for
independent clinical validation. **It is not yet considered clinically
validated or production-ready.** Per this program's explicit mission, it is
approved only to enter **Prospective Shadow-Mode Clinical Validation** —
advancing to `Pilot`/`Production` requires that separate, independent
clinical validation process, not just this checklist.
