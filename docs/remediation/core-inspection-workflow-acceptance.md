# Core Inspection Workflow — Manual Acceptance Script

This script exercises the canonical inspection workflow — create → upload →
analyze → honest result → submit for review → supervisor confirm/correct/
finalize — through the real running frontend and backend, as required by
the Core Inspection Workflow Closure sprint. It complements (does not
replace) the automated coverage in
`backend/tests/test_core_inspection_workflow_closure.py` and the existing
`test_inspection_role_permissions.py` / `test_clinical_readiness.py` /
`test_ai_clinical_review.py` suites.

**Environment**: backend (`uvicorn`, `ENABLE_DEV_AUTH=true`) + frontend
(`vite dev`) running together, `CORS_ORIGINS` including the frontend's dev
origin. Auth is set via `localStorage` (`token`/`role`/`actor`), matching
`frontend/src/lib/auth.tsx`.

---

## Scenario 1 — Technician successful inspection

- **Role**: operator
- **Test data**: facility "QA Facility", technician "QA Tech", tray "QA Tray",
  instrument "Kerrison Rongeur" (`kerrison_rongeur`), one valid PNG image, a
  manufacturer baseline registered for `kerrison_rongeur`.
- **Steps**:
  1. Sign in as operator, open `/inspection/new`.
  2. Fill in all required fields.
  3. Attach one image via the file input.
  4. Click "Submit Inspection".
- **Expected UI**: submit button shows a busy/submitting state during the
  request; on success, an "AI Prediction" panel renders showing: the
  "Experimental — Not Validated" banner, a "Model Result" section with
  `supported_categories` (debris, corrosion), any scored findings for those
  categories only, an explicit "Not evaluated by current model" list for
  every other category, and a "Full KPI detail" expandable section.
- **Expected API behavior**: `POST /api/inspections` returns `201` with
  `analysis.analysis_status == "completed"`, `analysis.model_result.findings`
  containing only `debris`/`corrosion` entries, and
  `supervisor_review_required` reflecting whether the disposition engine
  requires a human before release.
- **Expected audit event**: `inspection_created` and
  `inspection_analysis_succeeded` rows in the audit log for this inspection's
  `resource_id`.
- **Pass/Fail**: ______

---

## Scenario 2 — Viewer denied analysis

- **Role**: viewer
- **Test data**: none required.
- **Steps**:
  1. Sign in as viewer, open `/inspection/new`.
  2. Confirm no "Submit Inspection" or "Run AI Analysis" control is present.
  3. Attempt `POST /api/inspections` directly (e.g. via curl/devtools) with a
     viewer bearer token.
- **Expected UI**: the New Inspection form renders with no submit/analysis
  action available to a viewer.
- **Expected API behavior**: the direct API call returns `403` with an
  actionable message ("Viewer access is read-only...").
- **Expected audit event**: none required beyond the frontend's existing
  role-permission-failure error log (`POST /api/pilot-deployment/error-log`)
  fired by `apiFetch` on any `403`.
- **Pass/Fail**: ______

---

## Scenario 3 — Model unavailable

- **Role**: operator
- **Test data**: any valid inspection payload with an image. (To force the
  failure path in a test environment, monkeypatch/stub
  `app.routes.inspections.analyze_inspection` to raise, as done in
  `TestAnalysisFailureSafety` in the automated suite — there is no
  user-facing switch to force this in a live deployment today, since the
  current placeholder scoring pipeline has no external dependency that can
  go down.)
- **Steps**:
  1. Submit a new inspection while analysis is forced to fail.
- **Expected UI**: the inspection still submits successfully; the AI
  Prediction panel shows an honest "analysis unavailable" result rather than
  a crash or a fabricated finding.
- **Expected API behavior**: `POST /api/inspections` still returns `201`
  (the inspection is saved), with `analysis.analysis_status ==
  "analysis_unavailable"`, `supervisor_review_required == true`, and
  `analysis.model_result.findings == []`. The request never raises an
  unhandled 500.
- **Expected audit event**: `inspection_analysis_failed`.
- **Pass/Fail**: ______

---

## Scenario 4 — Supervisor confirms result

- **Role**: admin or spd_manager
- **Test data**: an existing inspection from Scenario 1.
- **Steps**:
  1. Sign in as admin/spd_manager, open the inspection's Clinical Decision
     panel (rendered inline after submission, or via the case's detail view).
  2. Review the Disposition Evidence Panel (coverage, readiness score,
     recommended disposition, risk stratification).
  3. Select "Approve" in the Supervisor Disposition Workspace and click
     Submit (no reason required for `approve`).
- **Expected UI**: "Disposition action recorded." confirmation message;
  submit button disabled while busy.
- **Expected API behavior**: `POST /api/inspections/{id}/disposition-action`
  returns `201`; the inspection's workflow state advances to `Completed`;
  the original `analysis` snapshot on the inspection row is unchanged.
- **Expected audit event**: `disposition_action_approve`, with `from_state`
  in its details.
- **Pass/Fail**: ______

---

## Scenario 5 — Supervisor corrects result with reason

- **Role**: admin or spd_manager
- **Test data**: a second inspection from Scenario 1 (not yet finalized).
- **Steps**:
  1. Open the Supervisor Disposition Workspace for the inspection.
  2. Select "Request Reclean".
  3. Attempt to submit with an empty reason — confirm the submit button is
     disabled/blocked client-side.
  4. Enter a reason ("visible residue on hinge") and submit.
- **Expected UI**: submit is blocked until a non-empty reason is entered;
  after submit, "Disposition action recorded." appears.
- **Expected API behavior**: submitting with an empty reason returns `422`
  (`ReasonRequiredError`); submitting with a reason returns `201`. The
  original AI output (`risk_level`, `recommended_action` on the inspection
  row) is unchanged; the correction is recorded as a new, separate
  `DispositionOverride` row alongside it.
- **Expected audit event**: `disposition_action_reclean`, with `reason` in
  its details.
- **Pass/Fail**: ______

---

## Scenario 6 — Missing image

- **Role**: operator
- **Test data**: an upload request with an empty file.
- **Steps**:
  1. Attempt to upload a 0-byte file via `POST /api/inspections/upload-images`.
- **Expected UI**: the upload UI surfaces the rejection as an error, not a
  silent no-op.
- **Expected API behavior**: `422` with a message naming the empty file.
- **Expected audit event**: none (rejected before any record is created).
- **Pass/Fail**: ______

---

## Scenario 7 — Invalid state transition

- **Role**: admin or spd_manager
- **Test data**: an inspection already finalized via Scenario 4 (`approve`).
- **Steps**:
  1. Attempt a second disposition action (e.g. "Request Reclean" with a
     reason) on the same, already-approved inspection.
- **Expected UI**: the action is rejected; the panel should surface the
  server's error rather than silently succeeding (server enforces this even
  if the UI does not yet grey out the controls after finalization).
- **Expected API behavior**: `409 Conflict` — "Inspection ... is already
  finalized ... No further disposition actions are allowed."
- **Expected audit event**: none written for the rejected attempt (no state
  change occurred).
- **Pass/Fail**: ______

---

## Scenario 8 — Hard refresh on inspection and review routes

- **Role**: any authenticated role
- **Test data**: none.
- **Steps**:
  1. Navigate to `/inspection/new`, then perform a hard browser refresh
     (Ctrl+Shift+R / Cmd+Shift+R).
  2. Repeat for the inspection review surface (Clinical Decision panel /
     inspection work queue route).
- **Expected UI**: the page re-renders fully (form or review panel), not a
  blank white page. The Readiness Disposition Panel now renders an explicit
  loading state while its evidence/risk fetches are in flight, and an
  explicit error state with a Retry button if either fetch fails — it no
  longer silently renders nothing on failure.
- **Expected API behavior**: n/a (client-side routing/rendering check).
- **Expected audit event**: n/a.
- **Pass/Fail**: ______
