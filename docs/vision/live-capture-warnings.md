# Live Capture Warnings (v2.3)

`POST /api/inspections/preview-warnings` — `app/routes/vision_session.py`.

## Why

v2.2's missing-anatomy and duplicate-detection warnings only appeared on the
Vision Session review page, after the inspection was already submitted. This
endpoint reuses the same two stateless services —
`app/services/vision_session_engine.py`'s `missing_anatomy_prompts()` and
`app/services/duplicate_detection_service.py`'s `detect_all()` — against the
technician's in-progress capture, before submission.

## Request

```json
{
  "instrument_type": "scissors",
  "tags": [
    {"anatomy_zone": "blade", "instrument_family": "scissors", "image_sha256": "…"}
  ]
}
```

Nothing is persisted and no `inspection_id` is required — `tags` describes
images the technician has captured and tagged so far but not yet submitted.

## Response

```json
{
  "missing_anatomy": {"prompts": [...], "suggested_next": "box lock"},
  "duplicate_detection": {"findings": [...], "has_warnings": true, "count": 1}
}
```

Same shape as the corresponding fields on `GET /api/inspections/{id}/vision-session`.

## Frontend

`frontend/src/pages/NewInspectionPage.tsx` hashes each captured image
client-side (`crypto.subtle.digest("SHA-256", ...)`, cached per file so a
re-render never rehashes an unchanged file) and calls this endpoint
debounced (500ms) whenever the instrument type, captured images, or image
tags change. Warnings render inline in the capture form, alongside the
existing Guided Capture panel and per-image tagging UI — the technician sees
"you have not captured the box lock" or "these two images are identical"
while they can still act on it, not after the record is already saved.
