# Dataset Registry

**Status:** New this pass (Dataset Registry & AI Model Development Foundation).
**Code:** `backend/app/models/dataset_governance.py` (`DatasetVersion`,
`DatasetRegistryEntry`), `backend/app/services/ml/dataset_registry.py`.
**API:** `POST/GET /api/dataset-registry/versions`,
`POST /api/dataset-registry/versions/{id}/freeze`,
`POST/GET /api/dataset-registry/images`.
**Tests:** `backend/tests/test_dataset_registry.py::TestDatasetRegistration`,
`::TestDatasetVersioning`.

This document describes the governed registry that tracks every image
admitted for ML training/evaluation. It complements, and does not replace,
pre-existing ML-governance infrastructure already in this repository:

- `app.models.retained_image.RetainedImage` — the actual retained bytes
  (opt-in, EXIF-stripped). The registry references a `RetainedImage` by ID
  (`retained_image_id`) rather than storing bytes again.
- `app.models.veritas_evidence.VeritasTrainingDatasetEntry` — an earlier,
  narrower training-data-assurance gate for one retained-image/label pair.
  The registry is the broader, full-metadata record this program's brief
  requires; both can coexist and reference the same underlying image.
- `app.models.model_registry.ModelRegistryEntry` — what gets trained, not
  what it was trained on.

## Every registered image carries

| Field | Column | Notes |
|---|---|---|
| Dataset ID | `dataset_version_id` | FK to `DatasetVersion.id` |
| Image ID | `id` (this row) / `retained_image_id` | references the real stored bytes |
| Inspection ID | `inspection_id` | nullable — not every training image originates from a live inspection |
| Instrument Family | `instrument_family` | required at registration |
| Instrument Model | `instrument_model` | optional |
| Manufacturer | `manufacturer` | required at registration |
| Anatomy Zone | `anatomy_zone` | optional |
| Inspection Date | `inspection_date` | nullable |
| Capture Device | `capture_device` | required at registration |
| Image Resolution | `image_resolution` | required at registration, `"WxH"` |
| Lighting Condition | `lighting_condition` | defaults `"unknown"` |
| Image Quality | `image_quality` | set by the real quality assessment — see `ANNOTATION_GUIDE.md` |
| Facility | `facility` | required at registration |
| Operator | `operator` | required at registration |
| Current Label | `current_label` | set during annotation, empty until then |
| Reviewer | `reviewer` | set during annotation |
| Review Status | `review_status` | the 7-state annotation lifecycle — see `ANNOTATION_GUIDE.md` |
| Annotation Version | `annotation_version` | increments on every non-archive transition |
| Dataset Version | `dataset_version_label` | denormalized copy of the version's label at registration time |
| Split Assignment | `split_assignment` | set by the dataset builder — see below |
| Usage Rights | `usage_rights` | free text (e.g. "consented-in-workflow", "manufacturer-reference") |
| PHI Verification | `phi_verification` | `pending` \| `verified` \| `rejected` |
| Training Eligibility | `training_eligibility` | boolean, false until explicitly marked eligible |
| Retention Status | `retention_status` | `active` \| other retention states |

All metadata is stored in real, typed columns — not a JSON blob — so
validation and querying (e.g. "how many facilities are represented?") stay
honest and enforceable rather than ad hoc.

## Registration requirements (Section 1 / 14)

`dataset_registry.register_image()` enforces, in order:

1. The target `DatasetVersion` exists and is **not frozen** (see below).
2. Required metadata is present: `instrument_family`, `manufacturer`,
   `facility`, `operator`, `capture_device`, `image_resolution`. Missing
   fields raise `MetadataValidationError` naming exactly which ones.
3. The image is not already registered for this tenant (duplicate
   detection by `image_sha256`) — raises `DuplicateImageError` naming the
   existing entry.

## Dataset versioning (Section 2)

`DatasetVersion` is a first-class, freezable entity — distinct from the
free-text `dataset_version`/`dataset_version_label` strings copied onto
individual rows for convenience.

- `dataset_registry.create_dataset_version()` creates (idempotently, per
  tenant + label) a version like `v0.1`, `v0.2`, `v1.0`.
- `dataset_registry.freeze_dataset_version()` makes it **immutable**:
  records `frozen_at`/`frozen_by`/`image_count_at_freeze`, and every
  subsequent `register_image()` call against that version raises
  `DatasetVersionFrozenError`.
- A correction to a frozen version's contents requires a **new** version
  referencing it via `supersedes_id` — never a silent edit of history.

## Split assignment (Sections 6 & 7)

Split assignment is written by `app.services.ml.dataset_builder.
build_training_dataset()`, which reuses the pre-existing, leakage-safe
`app.services.ml.dataset_split.split_dataset()` (see `TRAINING_PIPELINE.md`)
rather than re-implementing splitting.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/dataset-registry/versions` | create a dataset version |
| `GET` | `/api/dataset-registry/versions` | list versions |
| `POST` | `/api/dataset-registry/versions/{id}/freeze` | make a version immutable |
| `POST` | `/api/dataset-registry/images` | register an image |
| `GET` | `/api/dataset-registry/images` | list registered images |
| `POST` | `/api/dataset-registry/versions/{id}/build-training-dataset` | apply exclusion filters, report balance, assign splits |

All write endpoints require `admin`/`spd_manager`; reads are open to
`operator`/`viewer` as well.
