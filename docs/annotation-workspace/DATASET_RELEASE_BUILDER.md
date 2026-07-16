# Dataset Release Builder Guide

Source: `app/services/dataset_release_service.py`
(`build_release_preview()`),
`app/services/dataset_export_preview_service.py` (`preview_export()`),
`GET /api/dataset-release/preview`,
`GET /api/dataset-release/export-preview?export_format=`, frontend
`DatasetReleaseBuilderPage.tsx` (`/dataset/releases`).

## Who may access

`ROLES_MAY_EXPORT` — `admin`/`ai_researcher` only, enforced at the route
(`403` for every other role, including Reviewer/Clinical Reviewer).

## Bridging two governance tracks

A dataset image is release-ready only when **both** tracks agree:

1. **Annotation-level Ground Truth** — the linked `Annotation`'s
   `ground_truth_status == "ACTIVE"` (`docs/annotation-database/
   GROUND_TRUTH_MODEL.md`).
2. **Registry-entry-level structural eligibility** —
   `dataset_eligibility_service.compute_entry_eligibility()` resolves to
   one of the four release-ready states: `ground_truth_approved`,
   `eligible_for_training`, `eligible_for_validation`, or
   `eligible_for_testing`.

This means a Ground-Truth-approved annotation whose underlying image is
rights-restricted (blank `usage_rights`) or was later marked
`image_quality = "Reject"` is still correctly excluded from every release
candidate list — verified by
`test_rights_restricted_image_excluded_from_release_candidates` and
`test_rejected_quality_image_excluded_from_release_candidates`.

## What the preview reports

Candidate entry IDs, label/facility/manufacturer/instrument-family
distribution, duplicate groups (by `sha256`), and a non-persisted
`split_preview` (via the pre-existing `dataset_split.split_dataset()` +
`has_no_group_leakage()`) — actual split assignment is still performed by
the pre-existing `dataset_builder.build_training_dataset()` endpoint;
this preview never writes split assignments itself.

## Export preview

Wraps the pre-existing `annotation_export_service.export_annotations()`
(7 formats: `classification`/`yolo`/`coco`/`pascal_voc`/`segmentation`/
`csv`/`json`) and adds `class_distribution`, `missing_data_warnings` (e.g.
a whole-image annotation has no bounding box, so a `yolo` export reports
it rather than fabricating a region), `dataset_versions`, and
`ground_truth_versions`. An unknown `export_format` returns `422`.

## Freezing a version

Delegates to the pre-existing `dataset_registry.freeze_dataset_version()`
route, guarded by a `window.confirm()` in the UI since freezing is
effectively irreversible for that version (`IMAGE_INGESTION_GUIDE.md`
documents that a frozen version then rejects new ingestion with `409`).

## Tests

`backend/tests/test_dataset_release.py`,
`backend/tests/test_project_canvas_checklist.py` (the two
rights/quality-exclusion tests above).
