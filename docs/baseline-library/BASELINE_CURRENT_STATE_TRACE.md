# Baseline Current-State Trace — Project Atlas Sprint 1

Written before any code changes for this sprint, per the mission's "inspect
the repository before editing" requirement. All paths, field lists, and
line references below were captured by direct repository reading, not
inferred.

## 1. What a baseline currently stores

**`BaselineLibraryEntry`** (`app/models/baseline_library.py:11-26`, table
`baseline_library`) is the model the live scoring path
(`baseline_comparison_scoring_service.resolve_baseline()`) and the LCID
pipeline (`lcid_service.resolve_baseline_id()`) both read. Its fields:

```
id, udi, instrument_category, manufacturer_name, model_name,
baseline_type,        # manufacturer / vendor / network_contributed
baseline_version,     # default "1.0"
approval_status,      # pending / approved / deprecated
approved_by, approved_at,
contributing_facilities,
governance_notes,     # free Text — sometimes holds "image_sha256=..." as a string
created_at
```

**It has no image field of any kind** — no `storage_uri`, no `image_bytes`,
no hash column. `POST /baselines/manufacturer`
(`app/routes/inspections.py:205-259`) creates one of these rows with
`governance_notes=f"image_sha256={body.image_sha256}"` — the hash is
stashed as a string inside a free-text notes column, and the companion
`POST /baselines/upload-images` (`app/routes/inspections.py:1089-1131`)
computes a SHA-256 per uploaded file but **never persists the bytes
anywhere** — no DB row, no object storage call. The frontend's
`CreateManufacturerBaseline.tsx` flow silently loses every image a user
uploads through it today.

## 2. Where image records currently live

Two real, already-built pipelines hold actual image bytes and real
governance metadata — neither is connected to `BaselineLibraryEntry`:

- **`RetainedImage`** (`app/models/retained_image.py:35-79`) — the single
  owner of raw bytes (`image_bytes: LargeBinary`) anywhere image bytes are
  retained server-side. Opt-in (`RETAIN_INSPECTION_IMAGES` + `consent_recorded`),
  EXIF-stripped, de-identified filenames. `sha256` column is the identity.
- **`DatasetRegistryEntry`** (`app/models/dataset_governance.py:128-209`) —
  the LCID-registered image record: one row per registered image, with
  `retained_image_id` (→ the actual bytes), `lcid` (permanent
  `LCID-YYYY-NNNNNNNNN` identifier), `instrument_family`, `manufacturer`,
  `anatomy_zone`, `image_quality`, `usage_rights`, `phi_verification`,
  `digital_twin_id`, `baseline_id` (an existing **soft FK** into
  `baseline_library.id` — see Section 3), `image_type` (already includes a
  `baseline_reference` value), `catalog_number`, `inspection_region`. This
  is "the existing LCID image entity" this sprint's mission refers to.
  Registered via `dataset_registry.register_image()`
  (`app/services/ml/dataset_registry.py:117-224`), which validates the
  target `DatasetVersion` isn't frozen, enforces required metadata fields,
  rejects duplicates by `(tenant_id, image_sha256)`, and calls
  `lcid_service.generate_lcid()`.
- **Two OTHER, unrelated models already attach real image files to a
  "baseline" concept**, confirming the gap is specifically in
  `BaselineLibraryEntry`, not in the platform's storage capability:
  - `EnterpriseInstrumentBaseline` (`app/models/enterprise_quality.py:161`)
    — `storage_uri`/`content_type` via `app.services.object_storage`,
    populated by `POST /api/enterprise/instruments/{id}/baseline`.
  - `EnterpriseVendorBaselineSubscription`
    (`app/models/enterprise_quality.py:212`) — `baseline_image_url` (Text),
    populated by the Vendor Baseline Portal upload flow.
  Neither of these is read by `dataset_registry`, `Annotation`, LCID, or the
  live scoring path — they are a completely separate enterprise-intake
  silo (see Section 6).

## 3. Whether baseline IDs reference images — and the full baseline inventory

`DatasetRegistryEntry.baseline_id` is a **soft** FK to
`baseline_library.id` (not enforced at the DB level; validated for orphans
in `dataset_validation_service`, per its own field comment) — this link
already exists in the schema, in the *direction* "this registered image was
compared against this baseline entry," but there is no reverse structure:
`BaselineLibraryEntry` has no way to say "here is the image that represents
me." That reverse link is exactly what this sprint adds.

Nine distinct persisted "baseline" concepts already exist in this
codebase. Enumerated here so this sprint does not become a tenth:

| Model | File | Has image bytes? | Wired to LCID/Annotation/live scoring? |
|---|---|---|---|
| `BaselineLibraryEntry` | `models/baseline_library.py:11` | No | **Yes** — the one this sprint extends |
| `EnterpriseBaseline` | `models/enterprise_hierarchy.py:113` | No | No — enterprise-wide policy/acceptance-criteria record |
| `EnterpriseInstrumentBaseline` | `models/enterprise_quality.py:161` | Yes (`storage_uri`) | No |
| `EnterpriseVendorBaselineSubscription` | `models/enterprise_quality.py:212` | Yes (`baseline_image_url`) | No |
| `BaselineDecisionPolicy` | `models/lumen_decision_engine.py:59` | No | N/A — a decision-threshold policy, not an image entity |
| `BaselineGovernanceRecord` | `models/p24_standards.py:42` | No | No — governance/audit trail for a baseline event |
| `VendorBaselineExternalRecord` | `models/integrations.py:212` | No | No — external EDI/vendor-feed import record |
| `VendorBaselineAuditEvent` | `models/vendor_baseline_audit.py:10` | No | No — append-only audit log keyed by `baseline_id` |
| `ManufacturerBaselineQuality` | `models/vendor_intelligence.py:142` | No | No — analytics rollup, not an entity |

This sprint's scope is `BaselineLibraryEntry` specifically — it is the only
one of the nine already wired into the LCID pipeline and the live
inspection scoring path (`resolve_baseline()`), matching the mission's
"convert LumenAI's existing baseline metadata registry." The other eight
are out of scope and are left untouched; they are documented here so a
future reader does not rediscover them as candidates to merge in without
first reading this table.

## 4. How baseline resolution works today

`baseline_comparison_scoring_service.resolve_baseline(db, instrument_type,
tenant_id)` (lines 533-557) checks, in order: `_resolve_from_library`
(`BaselineLibraryEntry`, manufacturer → vendor → hospital priority via
`baseline_type`) then `_resolve_from_uploaded`
(`EnterpriseVendorBaselineSubscription` — a second, parallel path bridged
in specifically because "uploaded baselines are invisible to the scoring
engine" without it, per that function's own docstring). Neither path ever
resolves an image — both return metadata (manufacturer name, version,
approval status) used purely to gate whether *any* score may be computed at
all, never to compare pixels.

`baseline_comparison_service.compare_to_baselines()` (Project Canvas
Section 14, `app/services/baseline_comparison_service.py`) is a separate,
newer function that resolves 4 baseline "buckets" for one
`DatasetRegistryEntry`: manufacturer/vendor (`BaselineLibraryEntry`),
organization (`BaselineLibraryEntry` filtered to
`network_contributed`), digital-twin (sibling `DatasetRegistryEntry` with
the same `digital_twin_id` and `image_type == "baseline_reference"`), and
research (sibling entry with `image_type == "research_reference"` and
`review_status == "APPROVED"`). This function already implements a
resolution *pattern* very close to what Section 8 of this sprint's mission
asks for, but only within the Annotation/Canvas review-workspace context —
it is not consulted by the live per-inspection scoring path at all.

## 5. Why the live comparator currently has no actual baseline image

`image_similarity_service.py` (Project Lens Section 18) is a real,
first-stage perceptual-hash (average-hash) comparator:
`compare_image_bytes(image_a, image_b)` and `compare_against_baseline(...)`
— fully implemented, unit-tested (`tests/test_project_lens.py`), and
defines exactly the compatibility-first contract this sprint's Section 7
describes (`STATUS_NO_APPROVED_BASELINE`, `STATUS_INCOMPATIBLE_VIEW`, etc.,
never fabricating a similarity score when compatibility fails). A
repo-wide grep confirms **no route anywhere calls it** — it is dead code
from the live path's perspective, not because the algorithm is unproven,
but because there has never been a baseline *image* to hand it as the
second argument. `BaselineLibraryEntry` (Section 1) has none, and the two
models that do have image bytes (Section 2) are never queried by anything
that could supply this function's `baseline_image_bytes` parameter. This
sprint closes that gap directly: it does not touch
`image_similarity_service.py` itself, it gives it something real to
compare against.

## 6. Frontend baseline pages today

Three non-integrated upload UIs and one placeholder "library" page exist,
confirmed by direct reads of `frontend/src/main.tsx`'s route table:

| Route | Component | Behavior |
|---|---|---|
| `/manufacturer-baselines` | `ManufacturerBaselinesPage.tsx` | Uploads via `/api/baselines/upload-images` (discards bytes — Section 1) then `/api/baselines/manufacturer` |
| `/baseline-review` | `BaselineReviewPage.tsx` | Reads `/api/enterprise/baseline-review-queue` (vendor-subscription queue, unrelated model) |
| `/vendor-baseline-portal` | `VendorBaselinePortalPage.tsx` | Full CRUD against `/api/enterprise/vendor-baseline-subscription/...` |
| `/baseline-library` | **`BaselineLibraryPage.tsx`** | **Pure placeholder** — "Full search and filtering will be available in the next release," with two outbound links. This is the page this sprint builds out. |
| `/baseline-image-upload` | `BaselineImageUploadPage.tsx` | Real upload via `object_storage`, into `EnterpriseVendorBaselineSubscription` |
| `/baseline-readiness` | `BaselineReadinessPage.tsx` | Reads `EnterpriseBaseline` rows — unrelated |

Per the mission's "do not duplicate the existing Manufacturer Baselines
page; integrate or refactor it," this sprint builds the real workspace
into the already-placeholder `/baseline-library` route (and its `:baselineId`
/`/new` children, per Section 10 of the mission) rather than adding an
eleventh page, and leaves the other five pages untouched — they serve the
separate enterprise-intake baseline concepts documented in Section 3.

## 7. Reusable components confirmed for this sprint

- **Digital Twin identity**: NOT `app/models/digital_twin.py` (that is an
  unrelated SPD-workflow-throughput simulation — `SPDWorkflowStation`,
  `TwinSnapshot`, etc.). The real per-physical-instrument identity used for
  baselining is `lcid_service.instrument_digital_twin_id(...)`
  (`app/services/ml/lcid_service.py:42-50`) — a stable string key
  (`barcode:...` / `udi:...` / `untracked:...`), already stored on both
  `DatasetRegistryEntry.digital_twin_id` and `Annotation.digital_twin_id`.
  `is_untracked_twin(id)` flags the honest "no real identifier captured"
  case.
- **Ground Truth**: `Annotation.ground_truth_status == "ACTIVE"` is set
  only by `annotation_ground_truth_service.promote_to_ground_truth()`,
  which requires `actor_role` in `ROLES_MAY_FINALIZE_GROUND_TRUTH =
  {admin, clinical_reviewer}` and a real `AnnotationReview` with
  `agreement is True` or a resolved adjudication — never AI confidence
  alone.
- **RBAC**: `app/authz.py::require_roles(*roles)` — simple role-string
  check off `get_current_user`. Role vocabulary observed:
  `admin, spd_manager, operator, viewer, ai_researcher, clinical_reviewer`
  (the last two explicitly documented as free-form additive strings, not
  an enum, in `annotation_database.py:60-64`). `app/tenant_authz.py`'s
  `require_tenant_roles` additionally enforces real tenant membership.
  (The enterprise-intake silo uses a third, unrelated vocabulary —
  `hospital_admin`/`enterprise_admin` — out of scope here.)
- **Audit**: `enterprise_audit_service.record_enterprise_audit_event()`
  already accepts a first-class `baseline_id: int | None` parameter and is
  hash-chained (each event's hash includes the previous event's hash for
  the same resource). This sprint calls it directly rather than the
  deprecated `app.audit.log_audit_event` shim that `dataset_registry.py`'s
  routes still use.
- **CRUD/review pattern to copy**: `app/routes/dataset_registry.py`'s
  double-blind-review sub-resource pattern (`.../primary`, `.../independent`,
  `.../adjudicate`, each backed by a service function raising typed
  exceptions mapped to 409/422 by the route) is the direct template for
  this sprint's baseline-image review workflow.
- **Storage integrity precedent**: the false-PASS remediation sprint
  (`docs/model-development/FALSE_PASS_ROOT_CAUSE.md`, Section 2) already
  added a reload-bytes/recompute-SHA-256/reject-on-mismatch pattern in
  `app/routes/inspections.py::create_inspection()` for `RetainedImage` —
  this sprint's Section 9 storage-integrity requirement reuses that exact
  pattern for baseline images.

## 8. Duplicated/dead concepts discovered (do not extend)

- `POST /baselines/upload-images` (`app/routes/inspections.py:1089-1131`)
  computes and discards a hash — a genuine, pre-existing dead-end this
  sprint does not fix (the manufacturer-baseline creation flow is being
  superseded by the new Baseline Image Library workspace, not patched in
  place).
- The nine-way baseline sprawl in Section 3 is itself the most significant
  "duplicated concept" finding — none are merged in this sprint, but no
  tenth is added either.

## 9. Migration/DB registration requirements for new models

Five real Alembic revisions exist (`001` → `4b336d3ed612` →
`f29f1456bdec` → `a1ba6c5ed8f8` → `b7c3d9f1a204`, current head). A new
migration for this sprint's models must chain off `b7c3d9f1a204`. New model
modules must also be added to `tests/conftest.py::_force_import_models()`'s
import list (the file documents a real prior incident where a model
missing from that list silently had no test-DB table).
