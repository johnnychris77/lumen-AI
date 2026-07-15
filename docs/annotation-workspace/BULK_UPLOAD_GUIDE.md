# Bulk Upload Guide

Source: `backend/app/services/dataset_ingestion_service.py`
(`bulk_ingest()`, `parse_csv_metadata()`), `backend/app/routes/
dataset_ingestion.py` (`POST /api/dataset-ingestion/images/bulk`),
frontend `DatasetImageUploadPage.tsx`'s bulk section.

## Inputs

- One or more image files (`files: UploadFile[]`).
- `shared_metadata` — a JSON object applied to every row unless overridden
  by a matching CSV row (same required fields as
  `IMAGE_INGESTION_GUIDE.md`, minus `consent`/`dataset_version_id`, which
  are always passed as explicit top-level form fields — never duplicated
  inside `shared_metadata`).
- An optional CSV (`parse_csv_metadata()`) for per-row overrides keyed by
  filename, so a batch of images from different instruments/facilities
  doesn't need one upload per image.

## Partial success, never all-or-nothing

Each file is ingested independently through the same `ingest_image()`
path bulk upload shares with the single-image flow. One row's failure
(missing metadata, duplicate, unsupported type) does not abort the batch
— the response is a `BulkIngestResult` with a per-row outcome
(`ok`/`error` + reason), rendered as a row-level results table in the UI.
This mirrors the same duplicate-warning/validation-error semantics as
single-image ingestion, applied per row rather than once.

## What is never fabricated

No row is silently skipped without being reported; no row is marked
successful without a real `dataset_registry.register_image()` call
having actually persisted it.

## Tests

`backend/tests/test_dataset_ingestion.py::test_bulk_ingest_partial_success`
and the other bulk-path cases in the same file.
