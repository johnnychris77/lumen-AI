# Image Ingestion Guide

Source: `backend/app/services/dataset_ingestion_service.py`
(`ingest_image()`), `backend/app/routes/dataset_ingestion.py`
(`POST /api/dataset-ingestion/images`), frontend
`DatasetImageUploadPage.tsx` (`/dataset/images/upload`).

## Who may ingest

`ROLES_MAY_ANNOTATE` (Annotator/Reviewer/Clinical Reviewer/Administrator).
Viewer and AI Researcher are rejected with `403`.

## Minimum registration form

All fields are required unless noted; the route returns `422` with a
`missing_fields` list naming exactly which ones are absent — the same
list `dataset_registry.validate_metadata`/`REQUIRED_STRING_FIELDS` already
enforces for every other registration path, not a second validation rule
set:

`instrument_family`, `manufacturer`, `facility`, `operator`,
`capture_device`, `image_resolution`, `usage_rights`, `dataset_version_id`,
`consent` (checkbox, must be `true`). `image_type` defaults to
`after_use` if not supplied — one of the 7 `IMAGE_TYPES`.

## What happens on submit

1. `image_retention_service.retain_image()` — the image is de-identified
   and stored exactly as every other retention path in this codebase
   already does. If `RETAIN_INSPECTION_IMAGES` is not enabled, the route
   returns `404` (retention is genuinely disabled, never silently faked).
2. `dataset_registry.find_duplicate()` — a matching `sha256` against the
   same tenant returns a **warning**, not a hard block: the entry is still
   registered, but the response's `duplicate_of` field names the existing
   entry so a human can decide whether to keep both.
3. `dataset_registry.register_image()` — the real registration row is
   created; a real LCID (`lcid_service`) is resolved and returned, never
   fabricated.
4. `record_enterprise_audit_event()` — every successful ingestion writes
   an audit event.

## Error mapping

| Condition | HTTP status |
|---|---|
| Missing required metadata field | `422` |
| Retention disabled | `404` |
| Dataset version frozen (`freeze_dataset_version()` already called) | `409` |
| Unsupported image content type | `415` |
| File too large | `413` |
| Dataset version not found | `404` |

## Tests

`backend/tests/test_dataset_ingestion.py`,
`backend/tests/test_project_canvas_checklist.py::test_frozen_dataset_version_rejects_new_ingestion`.
