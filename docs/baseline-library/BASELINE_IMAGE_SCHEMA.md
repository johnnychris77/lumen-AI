# Baseline Image Schema — Project Atlas Sprint 1

Defines the new tables this sprint adds. All five live in
`backend/app/models/baseline_image_library.py`, registered via Alembic
revision `c1d4a7f2b8e6_add_baseline_image_library_tables` (chained off
`b7c3d9f1a204`) and in `tests/conftest.py::_force_import_models()`.

None of these tables store image bytes. Every image reference is a soft
pointer to an existing `DatasetRegistryEntry` (the LCID registry) and, via
that entry, to `RetainedImage.image_bytes` — see
`BASELINE_CURRENT_STATE_TRACE.md` Section 2 for why bytes are never
duplicated.

## `baseline_image_links`

The reverse link this sprint adds: which LCID-registered image represents a
given `BaselineLibraryEntry`, for which anatomy zone/view/orientation,
under what governance. One `BaselineLibraryEntry` may have many
`BaselineImageLink` rows (Section 3 of the mission — multiple images for
different anatomy zones/depths/orientations/views).

| Field | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `created_at` | datetime | |
| `tenant_id` | string(100) | tenant isolation scope |
| `facility_id` | string(100) | optional facility scoping within a tenant |
| `baseline_library_entry_id` | int | soft reference to `baseline_library.id` |
| `lcid_image_id` | int | soft reference to `dataset_registry_entries.id` (the LCID image) |
| `instrument_family`, `manufacturer`, `model_name`, `catalog_number` | string | denormalized/cached from the linked `DatasetRegistryEntry` at link time — always re-validated at activation, never trusted alone |
| `anatomy_zone`, `inspection_view`, `orientation` | string | what this specific image documents |
| `image_type` | string(30) | one of `BASELINE_IMAGE_TYPES` (Section 3) |
| `source_type` | string(40) | one of `BASELINE_SOURCE_TYPES` (Section 2) |
| `source_organization`, `source_reference` | string | real provenance evidence — required when `source_type` is `manufacturer_reference` |
| `baseline_version` | string(40) | default `"1.0"` |
| `effective_date` | datetime, nullable | |
| `lifecycle_status` | string(20) | one of `BASELINE_IMAGE_STATES` (Section 4) |
| `approved_by`, `approved_at` | string / datetime | set only by `review_baseline_image()` on `decision="approve"` |
| `usage_rights_status`, `image_quality_status` | string | cached from the linked LCID entry, re-verified at activation |
| `annotation_ref` | string(40) | points at `Annotation.ann_id` when a clinical annotation/Ground Truth record backs this image |
| `digital_twin_id` | string(255) | reused from `lcid_service.instrument_digital_twin_id()` |
| `image_sha256` | string(64) | cached storage-integrity hash (Section 9) |
| `retained_image_id` | int, nullable | soft reference to `retained_images.id` — the actual bytes |
| `superseded_at`, `supersedes_link_id`, `superseded_by` | | supersession trail (Section 4/6) — the old row is never edited or deleted |
| `created_by` | string(255) | |
| `limitations` | text | free-text caveats surfaced in the viewer |

## `baseline_image_reviews`

One row per authorized review decision (Section 5). A link may have
multiple reviews (resubmission after rejection); the link's own
`lifecycle_status` always reflects the latest decision.

| Field | Type | Notes |
|---|---|---|
| `id`, `created_at`, `tenant_id` | | |
| `baseline_image_link_id` | int | which link this reviews |
| `reviewer`, `reviewer_role` | string | actor identity/role at review time |
| `decision` | string(20) | `"approve"` or `"reject"` |
| `rationale` | text | required, non-empty |
| `limitations` | text | |
| `source_verification` | text | free-text notes on how source provenance was checked |
| `anatomy_compatibility_confirmed` | bool | |
| `image_quality_assessment` | string(20) | |
| `review_date`, `next_review_date` | datetime | |

## `baseline_sets`

Section 6 — a governed grouping of compatible `BaselineImageLink` rows for
one manufacturer/model + anatomy zone + view/orientation protocol +
version ("multiple known-good images instead of one perfect reference
image").

| Field | Type | Notes |
|---|---|---|
| `id`, `created_at`, `tenant_id` | | |
| `manufacturer`, `model_name`, `instrument_family` | string | scope |
| `anatomy_zone`, `view_protocol`, `orientation_protocol` | string | the compatible-image criteria this set enforces |
| `version` | string(40) | |
| `lifecycle_status` | string(20) | reuses the same `BASELINE_IMAGE_STATES` vocabulary |
| `active` | bool | |
| `limitations` | text | |
| `effective_date` | datetime, nullable | |
| `supersedes_set_id` | int, nullable | |

## `baseline_set_members`

Association table: one `BaselineImageLink` belongs to one `BaselineSet`. A
real relational join table, not a JSON id-list column, so membership is
queryable/indexable like any other governed relationship.

| Field | Type |
|---|---|
| `id` | int PK |
| `baseline_set_id` | int |
| `baseline_image_link_id` | int |
| `added_at` | datetime |

## `baseline_comparison_access_log`

Section 9/14 — every time a baseline image's bytes are loaded for
comparison (or the load fails hash verification), a real, queryable row is
written here in addition to the hash-chained audit event, so "comparison
access" and "hash verification failure" can be reported without parsing
audit-log `details` JSON.

| Field | Type | Notes |
|---|---|---|
| `id`, `created_at`, `tenant_id` | | |
| `baseline_image_link_id` | int | |
| `accessed_by` | string(255) | |
| `outcome` | string(30) | `verified` / `hash_mismatch` / `not_found` |
| `similarity` | float, nullable | reserved for a future real comparator result — never populated with a fabricated value today |
| `compatibility_status` | string(40) | |

## What is explicitly NOT in this schema

- No `LargeBinary`/bytes column anywhere in this module.
- No new "instrument" or "manufacturer" master table — those fields are
  cached copies of what `DatasetRegistryEntry` already owns.
- No new audit table — every lifecycle transition calls the existing
  `record_enterprise_audit_event()`.
