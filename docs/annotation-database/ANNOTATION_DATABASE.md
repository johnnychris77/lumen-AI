# LumenAI Annotation Database

**Status:** The authoritative source of truth for every AI observation,
expert annotation, adjudication, and ground truth label. Additive to, and
composed with, three pre-existing systems rather than a competing one:

| Existing system | What it already does | How this sprint composes with it |
|---|---|---|
| `app.models.dataset_governance` (`DoubleBlindReview`, `AnnotationEvent`) | Per-`DatasetRegistryEntry` review workflow | Unchanged; `Annotation` reuses the same `ANNOTATION_STATES` vocabulary but is a richer, image-level finding record — one dataset image may carry several `Annotation` rows |
| `app.services.ml.lcid_service` | Digital Twin identity (barcode/UDI-based), baseline resolution | Reused directly (`instrument_digital_twin_id`, `resolve_baseline_id`) — never re-implemented |
| `app.models.lumen_decision_engine.UnknownFindingReview` | AI-observation-triggered unknown-finding workflow | `Annotation`'s unknown-finding fields are a lighter, denormalized mirror for annotations that originate directly from human review rather than an AI observation |

## Core entity

`app.models.annotation_database.Annotation` — one row per finding, with a
permanent `ann_id` (`ANN-YYYY-NNNNNNNNN`), full relationship set (Section
2), observation storage (Section 3), region annotation (Section 4),
review-workflow status, Ground Truth status, version counter, baseline
linkage, and unknown-finding fields. See `ANNOTATION_SCHEMA.md` for the
complete field list.

## Immutability discipline

The `Annotation` row always reflects **current** state. Every change is
additionally captured, in full, as an immutable `AnnotationVersion`
snapshot (`ANNOTATION_SCHEMA.md` §Versioning) — history is never edited or
deleted, only appended to, mirroring the append-only pattern already used
by `app.services.workflow_state_service` and `AnnotationEvent`.

## No training outside this system

Every export (`annotation_export_service.export_annotations()`) defaults
to `ground_truth_only=True` — only annotations whose `ground_truth_status`
is `ACTIVE` (Section 6) are eligible. See `GROUND_TRUTH_MODEL.md`.

## See also

`GROUND_TRUTH_MODEL.md`, `ANNOTATION_SCHEMA.md`, `ANNOTATION_API.md`,
`REVIEWER_WORKFLOW.md`, `ADJUDICATION_GUIDE.md`, `ANNOTATION_ANALYTICS.md`.
