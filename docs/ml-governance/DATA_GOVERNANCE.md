# Data Governance — ML Training & Evaluation

**Status:** This document formalizes the governance rules the code in this
pass (and the pre-existing "Phase 17"/Veritas ML infrastructure) already
enforces; it does not describe aspirational policy disconnected from code.

## PHI

- No patient, face, name, MRN, or document may appear in a training image
  — this platform stores instrument images only. Enforcement today is
  procedural (capture guidance, retention consent) plus EXIF stripping on
  ingest (`app.services.image_retention_service.strip_exif`); there is no
  automated PHI-detection model in this codebase, and this document does
  not claim one exists.
- `DatasetRegistryEntry.phi_verification` (`pending`|`verified`|`rejected`)
  is a real, queryable field. The training-dataset builder
  (`app.services.ml.dataset_builder.eligible_entries()`) **excludes any
  entry not explicitly `verified`** — the default (`pending`) is
  exclusionary, not permissive; PHI verification must be a deliberate,
  recorded human action before an image can reach training.

## Usage rights

- `DatasetRegistryEntry.usage_rights` records the basis for use (e.g.
  "consented-in-workflow", "manufacturer-reference"). No enforcement logic
  currently blocks a specific usage-rights value from training — this is
  recorded for audit and future policy enforcement, consistent with this
  document's honesty principle (we do not claim gating that doesn't exist).

## Retention

- `DatasetRegistryEntry.retention_status` (default `"active"`) tracks
  whether an entry is still within its retention window. Combined with the
  pre-existing `app.models.retained_image.RetainedImage` (which itself is
  only ever populated with explicit consent — see
  `docs/ai/model-training-dataset-plan.md` §6), retention stays an
  explicit, auditable decision at every layer, never a default.

## Duplicate data

- Duplicate images are excluded from both registration
  (`dataset_registry.register_image()` raises `DuplicateImageError` for a
  repeat `image_sha256` within a tenant) and dataset building
  (`dataset_builder.eligible_entries()` also excludes any second copy of
  the same `image_sha256` within one dataset version, as a defense-in-depth
  check).

## Archived / rejected data

- `ARCHIVED` annotation-state entries and `Reject`-quality images are
  excluded from every training dataset built by `dataset_builder.
  build_training_dataset()` — never silently included.

## Dataset immutability

- Once a `DatasetVersion` is frozen (`dataset_registry.
  freeze_dataset_version()`), no image may be registered into it and its
  metadata is never edited. A correction requires a **new** version
  referencing the old one via `supersedes_id` — the full history of what a
  model was actually trained on is never rewritten.

## Balance reporting, not silent rebalancing

- `dataset_builder.balance_report()` reports class/facility/instrument-
  family/manufacturer distribution for every dataset build. This program
  deliberately does **not** implement automated oversampling/undersampling
  — a skewed dataset is surfaced to a human reviewer, not silently
  "fixed," so a promotion decision is made with full visibility into what
  the model actually saw.

## Human-in-the-loop, always

- No model may drive a clinical recommendation below `validated` approval
  status (`app.services.ml.deployment_gates`), and even a `validated`
  model's recommendation is always subject to supervisor override.
  `human_review_required` is `true` on every model view regardless of
  stage. This document does not change that invariant — the Dataset
  Registry & AI Model Development Foundation program adds traceability and
  process, not a path to bypass human review.

## No clinical or regulatory claims

- Nothing in this program's infrastructure claims FDA/regulatory clearance
  or validated clinical accuracy. `known_limitations` is required text on
  every registry entry; the auto-generated Model Card
  (`MODEL_CARD_TEMPLATE.md`) surfaces it, along with an explicit "no
  causation" and "no regulatory clearance" statement, on every model.
