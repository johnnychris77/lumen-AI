# Project Canvas — Manual Acceptance Test

12 scenarios a human reviewer should walk through against a live dev
server before signing off on the Annotation Workspace. Each records
role/steps/expected UI/expected API response/expected DB state/expected
audit event/pass-or-fail, per this sprint's Section 27 requirement. This
document is the walkthrough script; it does not itself constitute a
completed sign-off — a human must run it and check each box.

---

### Scenario 1 — Upload a known-good baseline image

- **Role:** Annotator (`operator`)
- **Steps:** Navigate to `/dataset/images/upload`. Select/create a dataset
  version. Fill the registration form with `image_type = baseline_reference`
  and all required metadata. Check consent. Upload a real image file. Submit.
- **Expected UI:** Success confirmation with the new entry's LCID.
- **Expected API:** `POST /api/dataset-ingestion/images` → `201`, body
  includes `lcid` and `id`.
- **Expected DB state:** New `DatasetRegistryEntry` row, `image_type =
  "baseline_reference"`, linked `RetainedImage` row via retention service.
- **Expected audit event:** `dataset_image_ingested` (or equivalent
  ingestion event) recorded for the actor.
- **Pass/Fail:** ______

### Scenario 2 — Upload an after-use image with complete metadata

- **Role:** Annotator
- **Steps:** Same as Scenario 1 but `image_type = after_use`, distinct
  `sha256` content.
- **Expected UI:** Success confirmation; entry appears in `/dataset/images`.
- **Expected API:** `201`.
- **Expected DB state:** New entry, `review_status = UNLABELED`.
- **Expected audit event:** Ingestion event recorded.
- **Pass/Fail:** ______

### Scenario 3 — Detect a duplicate upload

- **Role:** Annotator
- **Steps:** Re-upload the exact same image bytes used in Scenario 2 (same
  `sha256`) with different metadata.
- **Expected UI:** Registration succeeds but a duplicate warning banner
  names the earlier entry.
- **Expected API:** `201` with a non-null `duplicate_of` field.
- **Expected DB state:** A second entry is created (not blocked) —
  duplicates are surfaced, not silently merged or rejected.
- **Expected audit event:** Ingestion event recorded; no separate
  "duplicate" event is fabricated if none exists in code.
- **Pass/Fail:** ______

### Scenario 4 — Complete a primary annotation

- **Role:** Annotator, then Reviewer (`spd_manager`)
- **Steps:** As Annotator, open `/annotations?retained_image_id=<id>`,
  submit a new annotation via the inline form. As Reviewer, go to
  `/review/primary`, select the annotation, submit a primary review.
- **Expected UI:** Confirmation banner persists after submission; queue
  item disappears from Primary Review queue on reload.
- **Expected API:** `POST /api/annotations` → `201`; `POST /api/annotations/
  {id}/review/primary` → `201`.
- **Expected DB state:** `Annotation.review_status = LABELED`;
  `AnnotationReview` row with `primary_reviewer`/`primary_label` set.
- **Expected audit event:** Annotation-created and primary-review-submitted
  events.
- **Pass/Fail:** ______

### Scenario 5 — Complete a blind secondary review with agreement

- **Role:** Reviewer/Clinical Reviewer (different person from Scenario 4's
  primary reviewer)
- **Steps:** Go to `/review/secondary`, select the annotation from
  Scenario 4. Confirm the blind view shows no primary label/confidence/
  comments anywhere (including via browser devtools network inspection).
  Submit the same classification as the primary reviewer used.
- **Expected UI:** Blind view never shows primary content; after
  submission, an "agreement" confirmation renders and persists.
- **Expected API:** `GET .../blind-view` response contains no
  `primary_label`/`primary_confidence`/`primary_comments`/`agreement`/
  `primary_reviewer` keys; `POST .../review/secondary` → `201`.
- **Expected DB state:** `AnnotationReview.agreement = true`;
  `review_status` advances toward Ground Truth eligibility.
- **Expected audit event:** Secondary-review-submitted event.
- **Pass/Fail:** ______

### Scenario 6 — Complete a secondary review with disagreement

- **Role:** Reviewer/Clinical Reviewer
- **Steps:** Repeat Scenario 4-5 on a fresh annotation, but submit a
  **different** classification for the secondary review.
- **Expected UI:** Confirmation renders; the annotation subsequently
  appears in `/review/disagreements`.
- **Expected API:** `POST .../review/secondary` → `201`,
  `agreement: false` reflected in the subsequent `GET .../review` (admin/
  clinical_reviewer only).
- **Expected DB state:** `review_status = DISAGREEMENT`.
- **Expected audit event:** Secondary-review-submitted event.
- **Pass/Fail:** ______

### Scenario 7 — Adjudicate the disagreement

- **Role:** Clinical Reviewer or Administrator
- **Steps:** Go to `/review/adjudication`, select the disagreement from
  Scenario 6. Confirm both primary and secondary labels are visible
  side-by-side. Attempt to submit with an empty rationale (expect
  rejection), then submit with a non-empty `resolution` and `reason`.
- **Expected UI:** Empty-rationale attempt shows a validation error;
  valid submission shows a persisting confirmation banner.
- **Expected API:** Empty-reason attempt → `422`; valid attempt → `201`.
- **Expected DB state:** `AnnotationReview.adjudication_reason`/
  `resolution`/`resolved_at`/`adjudicator` populated.
- **Expected audit event:** `annotation_adjudicated`.
- **Pass/Fail:** ______

### Scenario 8 — Promote an approved annotation to Ground Truth

- **Role:** Clinical Reviewer or Administrator
- **Steps:** From `/ground-truth`, select an annotation in the "Eligible
  for Promotion" card (from Scenario 5 or 7) and promote it.
- **Expected UI:** Item moves from "Eligible for Promotion" to "Active
  Ground Truth" on reload.
- **Expected API:** `POST /api/annotations/{id}/promote-ground-truth` →
  `200`/`201`.
- **Expected DB state:** `ground_truth_status = "ACTIVE"`; an
  `AnnotationVersion` snapshot recorded.
- **Expected audit event:** Ground-truth-promotion event.
- **Pass/Fail:** ______

### Scenario 9 — Reject a poor-quality image from training eligibility

- **Role:** Administrator (or whichever role manages `image_quality`)
- **Steps:** Mark a registered entry's `image_quality = "Reject"`. View
  `/dataset/images/:imageId` or `GET /api/dataset-eligibility`.
- **Expected UI:** Entry shows an "Excluded" eligibility state with the
  quality-rejection reason.
- **Expected API:** `dataset-eligibility` reports
  `excluded_from_training` with a reason mentioning image quality.
- **Expected DB state:** No change to `training_eligibility` flag itself —
  exclusion is computed, not stored redundantly.
- **Expected audit event:** None required for a read-only eligibility
  computation.
- **Pass/Fail:** ______

### Scenario 10 — Block an image without usage rights

- **Role:** Any Viewer+
- **Steps:** View an entry with blank `usage_rights` in `/dataset/images/
  :imageId` or the Dataset Release Builder's candidate preview.
- **Expected UI:** Entry shows a "Rights Restricted" eligibility state;
  entry is absent from `/dataset/releases`' candidate list even if
  otherwise Ground-Truth-approved.
- **Expected API:** `dataset-eligibility` reports `rights_restricted`;
  `dataset-release/preview`'s `candidate_dataset_entry_ids` excludes it.
- **Expected DB state:** No change.
- **Expected audit event:** None required.
- **Pass/Fail:** ______

### Scenario 11 — Link an image to its Digital Twin and baseline

- **Role:** Viewer+
- **Steps:** Open `/dataset/images/:imageId` for an image with a resolved
  `digital_twin_id`/`baseline_id`. Confirm the instrument-context panel
  shows a chronological timeline of linked images, and the baseline
  context panel shows resolved manufacturer/organization/Digital-Twin/
  research buckets (or an honest "not available" per bucket).
- **Expected UI:** No bucket ever shows a fabricated comparison; timeline
  entries are in chronological order.
- **Expected API:** `GET .../baseline-comparison` and
  `lcid_service.digital_twin_history()`'s `timeline` field.
- **Expected DB state:** No change (read-only).
- **Expected audit event:** None required.
- **Pass/Fail:** ______

### Scenario 12 — Freeze and export the first dataset version

- **Role:** Administrator or AI Researcher
- **Steps:** In `/dataset/releases`, review the release preview
  (candidates, distribution, split preview, duplicate groups). Assign
  train/val/test splits. Freeze the dataset version (confirm the
  `window.confirm()` guard appears). Attempt a new image ingestion against
  the now-frozen version and confirm it is rejected. Generate an export
  preview in at least one format (e.g. `yolo`) and confirm any
  whole-image annotation is reported as a missing-region warning rather
  than a fabricated bounding box.
- **Expected UI:** Freeze requires confirmation; post-freeze ingestion
  attempt shows an error; export preview shows real counts and warnings.
- **Expected API:** Freeze → `200`/`201`; subsequent
  `POST /api/dataset-ingestion/images` against that version → `409`;
  `GET /api/dataset-release/export-preview?export_format=yolo` → `200`
  with `missing_data_warnings` populated where applicable.
- **Expected DB state:** `DatasetVersion.frozen_at`/`frozen_by` populated;
  no further entries can be registered against it.
- **Expected audit event:** Dataset-version-frozen event.
- **Pass/Fail:** ______

---

## Sign-off

| Scenario | Result | Reviewer | Date |
|---|---|---|---|
| 1–12 | | | |

All 12 scenarios must pass before this workspace is considered manually
verified end-to-end, in addition to the automated backend/frontend test
suites referenced throughout `docs/annotation-workspace/`.
