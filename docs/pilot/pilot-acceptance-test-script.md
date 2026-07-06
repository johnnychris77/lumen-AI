# Pilot Acceptance Test Script — v1.9

Run through these test cases against a live environment (dev server or
staging) before pilot go-live. Each case lists the concrete steps, the API
calls involved, and the expected result. All of these are covered by
automated tests in `backend/tests/test_pilot_deployment.py` and the
relevant v1.6–v1.8 test files — this script is for a **manual, live**
confirmation pass, not a replacement for the automated suite.

## Test Case 1 — Technician completes an inspection

1. Log in as an `operator`.
2. Navigate to New Inspection (`/inspection/new`).
3. Select an instrument type, tag anatomy zones, and upload an image.
4. Submit.

**Expected**: HTTP 201; the response includes a real `analysis` block (or
`supervisor_review_required: true` if no baseline exists) and a
`data_quality` block. The inspection appears in the Smart Inspection Queue
(`/inspection-work-queue`) with a real `workflow_state` of `Image
Capture`/`AI Analysis` — never a fabricated or blank status.

## Test Case 2 — Supervisor review and approval

1. Log in as `spd_manager`.
2. Open `/inspection-work-queue`, find the inspection from Test Case 1 in
   the "Supervisor Reviews" bucket (if the disposition engine flagged it).
3. Call `POST /api/inspections/{id}/disposition-action` with
   `{"action": "approve", "ai_recommended_disposition": "..."}`.

**Expected**: HTTP 201. `GET /api/inspections/{id}/workflow-state` shows a
new `Completed` (or the relevant) transition with a real `actor` and
`created_at` — the audit trail is real, not fabricated.

## Test Case 3 — Viewer access restriction

1. Log in as `viewer`.
2. Attempt `POST /api/inspections` (create).
3. Attempt `POST /api/inspections/{id}/disposition-action`.
4. Attempt `GET /api/inspection-work-queue`.

**Expected**: Steps 2 and 3 return **HTTP 403** with a clear message
(e.g. *"Viewer access is read-only. Ask an admin to assign Operator or
SPD Manager access to run inspections."*) — never a silent failure or a
500. Step 4 returns **HTTP 200** — viewing is allowed.

## Test Case 4 — Missing baseline

1. Submit an inspection (`POST /api/inspections`) for an instrument type
   with **no** approved `BaselineLibraryEntry`.

**Expected**: HTTP 201 (the inspection is still recorded), but
`score_status: "supervisor_review_required"`, `baseline_status:
"no_approved_baseline"`, and `data_quality.issues` includes a
`missing_baseline` entry with a clear message — never scored as if a
baseline existed.

## Test Case 5 — Missing anatomy zone

1. Submit an inspection with `has_image: true` but no `inspected_zones`.

**Expected**: `coverage_pct` is `null` (not fabricated as 0 or 100), and
`data_quality.issues` includes a `missing_anatomy_zone` entry.

## Test Case 6 — AI analysis completion

1. Submit an inspection with a real image hash and an approved baseline
   on file for that instrument type.

**Expected**: `analysis.analysis_status: "completed"`,
`score_status: "scored"`, `risk_score` populated, and the Smart Inspection
Queue shows a real `disposition` (Proceed to Packaging / Reclean / etc.)
derived from the actual finding, not a placeholder.

## Test Case 7 — Knowledge note capture

1. Log in as `spd_manager`. Submit a disposition action (reclean/repair/
   escalate) on an inspection.
2. Call `POST /api/inspections/{id}/teaching-point` with a real
   explanation and teaching point.

**Expected**: HTTP 201, `approval_status: "approved"` (auto-approved —
see `docs/knowledge/clinical-case-library.md`). The note appears in
`GET /api/knowledge/articles?category=teaching_point` and the associated
`ClinicalCase.educational_notes` is updated.

## Test Case 8 — Clinical report generation

1. Call `GET /api/inspections/{id}/readiness-report.pdf` for a real,
   scored inspection.

**Expected**: HTTP 200, `Content-Type: application/pdf`, a non-empty PDF
body. If report generation throws (simulate by an instrument type with no
baseline history, or via the automated
`test_report_generation_failure_returns_500_not_silent` test), the
response is a clear **HTTP 500** with `"...has been logged"` in the
detail — never a silent 200 with an empty or corrupt file.

## Reporting results

For each test case, record: pass/fail, the actual HTTP status/response
observed, and (for any failure) whether it reproduces against the
automated suite. Do not mark the pilot go-live checklist's "Go/No-Go"
section complete until every test case above has a recorded **pass**.
