# Project Veritas — Training Dataset Assurance

LumenAI AI Specialist, Section 15.

## Mirrors Sage's curation-gate pattern, extended

`veritas_training_dataset_service.evaluate_for_training` gates a real
`RetainedImage`/`ImageLabel` pair into a training-dataset status, following
the exact reference-by-ID pattern Sage's `SageEducationImageEntry`
established (`supervisor_validated` + `phi_review_status` + `usage_rights`),
extended with the training-specific checks this section names:

- correct instrument family / anatomy zone
- confirmed finding + severity label (from the image's gold `ImageLabel`)
- image quality threshold met (caller-supplied, since no real per-image
  quality score exists — see `image-quality-assessment.md`)
- duplicate detection (same `RetainedImage.sha256` as another image)
- provenance completeness (`sha256` + `consent_recorded` + `uploaded_by`
  all present)

## Dataset statuses

| Status | When |
|---|---|
| `quarantined` | duplicate image detected |
| `excluded` | no consent recorded |
| `pending_validation` | any other check fails (listed in `status_reason`) |
| `approved_for_training` | every check passes |

## Never allows unvalidated evidence into training

An image only reaches `approved_for_training` when it is gold-labeled
(`ImageLabel.is_gold`), PHI-cleared, rights-declared, and not a duplicate —
exactly the brief's "do not allow unvalidated inspection images into
approved training sets."

## API

```
POST /api/veritas/training-dataset/{retained_image_id}/evaluate
GET  /api/veritas/training-dataset?dataset_status=...
```
