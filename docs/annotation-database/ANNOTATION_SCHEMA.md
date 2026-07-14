# Annotation Schema

Source of truth: `backend/app/models/annotation_database.py`.

## `Annotation`

| Field | Section | Notes |
|---|---|---|
| `ann_id` | 1 | `ANN-YYYY-NNNNNNNNN`, immutable, generated once by `annotation_service.generate_annotation_id()` from a dedicated per-year `AnnotationSequenceCounter` — never derived from row count, never reused |
| `retained_image_id`, `inspection_id`, `instrument_family`, `instrument_model`, `manufacturer`, `digital_twin_id`, `baseline_id`, `reviewer`, `dataset_version_id`, `ground_truth_version`, `model_version` | 2 | Relationships. `digital_twin_id`/`baseline_id` resolved via `lcid_service` at creation, never fabricated |
| `primary_observation`, `secondary_observation`, `appearance_attributes_json`, `severity`, `location`, `confidence`, `reviewer_confidence`, `comments`, `recommendation`, `supervisor_required`, `unknown_flag`, `image_quality` | 3 | Observation storage |
| `region_type`, `region_coordinates_json` | 4 | One of `REGION_TYPES` (`bounding_box`/`polygon`/`segmentation_mask`/`point`/`whole_image_classification`/`future_3d`); coordinates normalized 0.0-1.0. `future_3d` is reserved and unimplemented — never fabricated |
| `review_status` | 6 | Reuses `dataset_governance.ANNOTATION_STATES` |
| `ground_truth_status` | 6 | `DRAFT` / `ACTIVE` — see `GROUND_TRUTH_MODEL.md` |
| `current_version` | 7 | Incremented on every `update_annotation()` call |
| `baseline_type`, `baseline_version`, `baseline_similarity`, `baseline_deviation` | 8 | One of `BASELINE_TYPES` (`manufacturer`/`hospital`/`digital_twin`/`research`) |
| `supervisor_classification`, `clinical_review_status`, `candidate_label`, `promotion_status` | 10 | Unknown-finding fields |

## `AnnotationVersion`

Append-only. `version_number`, `editor`, `reason`, `previous_version_id`,
and a full `snapshot_json` of every mutable field at that version — never
a diff-only record, so any historical version can be reconstructed exactly
without replaying prior versions.

## `AnnotationReview`

Primary + secondary + adjudicator fields, `agreement` (computed, never
assumed), `disagreement_reason`, `resolution`/`adjudication_reason`/`resolved_at`.

## `AnnotationSequenceCounter`

One row per calendar year; `last_sequence` increments atomically on every
`generate_annotation_id()` call.
