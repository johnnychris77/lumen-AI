# Baseline Image Library — Manual Acceptance Script

Ten scenarios per mission Section 17. Each lists the steps, the expected
UI behavior, the expected API response, the expected DB state, and the
expected audit event(s). All scenarios assume a tenant-scoped user
authenticated via the existing dev-token role map (`app/deps.py`) or an
equivalent JWT.

## 1. Register a manufacturer baseline image

**Steps**: As `spd_manager`, go to `/baselines/library/new`. Enter an
existing `baseline_library_entry_id`, select a registered LCID image,
choose source type `manufacturer_reference`.

**Expected without provenance**: Submitting with blank source organization
and source reference is rejected client-side (submit button/validation
message) and, if attempted directly against the API, `POST
/api/baseline-library/images` returns `422 ProvenanceRequiredError`. No row
is created.

**Expected with provenance**: Fill in source organization and source
reference. Submission succeeds; `POST .../images` returns `201` with the
new link in `DRAFT`. **DB**: one new `baseline_image_links` row,
`lifecycle_status="DRAFT"`, `source_type="manufacturer_reference"`,
`source_organization`/`source_reference` populated. **Audit**:
`baseline_image_proposed` event recorded for `resource_type="baseline_image_link"`.

## 2. Link to manufacturer/model/anatomy zone and submit for review

**Steps**: From the new link's detail page, click "Submit for review."

**Expected**: State moves `DRAFT → PENDING_REVIEW`. **API**:
`POST .../images/{id}/submit-for-review` returns `200` with the updated
link. **DB**: `lifecycle_status="PENDING_REVIEW"`. **Audit**:
`baseline_image_submitted_for_review`. The link now appears in
`/baselines/review`.

## 3. Review and activate

**Steps**: As `clinical_reviewer`, open the link from `/baselines/review`,
enter a rationale, confirm anatomy compatibility, choose an image quality
assessment, click Approve. Then click Activate.

**Expected review**: `POST .../images/{id}/review` with
`decision="approve"` returns `201`. **DB**: new `baseline_image_reviews`
row; link's `lifecycle_status="APPROVED"`, `approved_by`/`approved_at`
set. **Audit**: `baseline_image_approved`.

**Expected activation** (assuming all activation-gate conditions are met —
usage rights, PHI verification, image quality, anatomy zone/view
documented, an approving review, hash stored, version assigned):
`POST .../images/{id}/activate` returns `200`; `lifecycle_status="ACTIVE"`.
**Audit**: `baseline_image_activated`. The image is now eligible to be
resolved for a matching inspection.

**If a gate condition is missing**: `activate` returns `422` with a
`missing` list naming exactly which conditions failed (e.g. "PHI review is
not complete") — no partial activation occurs.

## 4. Resolve for a matching inspection

**Steps**: `POST /api/baseline-library/resolve` with a `CandidateContext`
matching the ACTIVE image's manufacturer, model, and anatomy zone.

**Expected**: Returns `resolution_scope="manufacturer_model_zone"` (or
`"digital_twin_exact"` if the candidate's Digital Twin ID matches exactly),
`baseline_image_link_id` set to the ACTIVE link's ID, and a
`resolution_reason` explaining the match. No numeric similarity is
returned — this is a resolution decision, not a comparison result.

## 5. Reject for a different anatomy zone

**Steps**: `POST /api/baseline-library/compatibility-check` with a
candidate whose `anatomy_zone` differs from the ACTIVE baseline image's
`anatomy_zone`, passing `baseline_image_link_id` for that image.

**Expected**: Returns `{"status": "INCOMPATIBLE_ANATOMY_ZONE"}` — never a
similarity number, never a silent `COMPATIBLE`.

## 6. Register an organization known-good baseline

**Steps**: As `admin`, link an LCID image with `source_type=
"organization_known_good"` (no provenance requirement — this source type
is not in `SOURCE_TYPES_REQUIRING_PROVENANCE`). Submit, review, activate as
in Scenarios 1–3.

**Expected**: Succeeds through the same lifecycle without requiring
`source_organization`/`source_reference`. Once ACTIVE, this image is
eligible for `resolution_scope="organization_family_zone"` resolution for
candidates in the same instrument family and anatomy zone that don't have
a more specific manufacturer/model match.

## 7. Register a Digital Twin initial baseline

**Steps**: Link an LCID image whose underlying `DatasetRegistryEntry` has a
real (tracked) `digital_twin_id`, with `source_type=
"digital_twin_initial_reference"` and `image_type="digital_twin_baseline"`.
Submit, review, activate.

**Expected**: Once ACTIVE, `POST .../resolve` with a candidate carrying the
*same* `digital_twin_id` returns `resolution_scope="digital_twin_exact"` —
this wins over any broader manufacturer/model match that might also exist
for the same instrument type.

## 8. Supersede a version

**Steps**: With baseline image A ACTIVE (version `1.0`), link and get
image B approved (version `2.0`) for the same baseline entry/zone. As
`spd_manager`, call `POST .../images/{A.id}/supersede` with
`{"new_link_id": B.id}`.

**Expected**: `200` returns both `superseded` (A, now `SUPERSEDED`,
`superseded_at`/`superseded_by` set) and `active` (B, now `ACTIVE`,
`supersedes_link_id=A.id`). **A's detail page remains fully viewable** —
its history, review record, and hash are all still present; it is marked
SUPERSEDED, never deleted. **Audit**: `baseline_image_superseded` on A's
resource ID.

## 9. Confirm a metadata-only legacy baseline cannot be compared

**Steps**: Identify a `BaselineLibraryEntry` with zero `BaselineImageLink`
rows (a pre-existing metadata-only entry). Call `GET
/api/baseline-library/legacy-report` as `admin`.

**Expected**: The entry's ID appears in `missing_image_evidence`, tagged
with `missing_image_evidence_marker="IMAGE_EVIDENCE_MISSING"`. Calling
`resolve` or `compatibility-check` for any candidate context that would
otherwise match this entry's instrument returns `NO_APPROVED_BASELINE` (no
ACTIVE image link exists to resolve to) — the entry's existence as
metadata never produces a fabricated comparison result.

## 10. Confirm cross-tenant denial

**Steps**: As a user in Tenant A, attempt `GET
/api/baseline-library/images/{id}` for a `baseline_image_links` row that
belongs to Tenant B.

**Expected**: `404 Not Found` (the route's tenant-scoped query never
matches the row — it behaves identically to the ID not existing at all,
never revealing that a cross-tenant row exists). The same holds for
`compatibility-check`/`resolve`: a Tenant-B-only ACTIVE baseline is never
returned to a Tenant A candidate; the result is `NO_APPROVED_BASELINE`,
identical to "nothing approved," not a distinguishable "exists but
isn't yours" signal.
