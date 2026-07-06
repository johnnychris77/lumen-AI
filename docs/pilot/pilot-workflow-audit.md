# Pilot Workflow Audit — v1.9

An end-to-end pass over the workflows a pilot site actually depends on:
login, dashboard, new inspection (image upload, instrument selection,
anatomy zone selection), AI analysis, supervisor review, knowledge
capture, clinical report, and inspection history. Findings are grouped by
severity; only real, verified gaps are listed — nothing here is
speculative.

## Critical

### 1. `/findings` ("Review Queue" / "Findings" nav links) shows fabricated demo data, not real inspections

`frontend/src/pages/FindingsQueuePage.tsx` renders a hardcoded
`sampleFindings` array (fictional facilities "ORC", "St. Francis", "St.
Mary's"; fictional finding IDs `F-1000`–`F-1007`) with **no `useEffect`,
no API call, and no connection to the real backend at all**. Two separate
nav entries ("Review Queue" and "Findings" in `AppShell.tsx`) point here.

This is the page a pilot supervisor would land on expecting to see
inspections awaiting review — instead they'd see permanently-stale fake
data with no way to act on a real inspection. The *real* supervisor review
workflow already exists and works (the v1.7 Smart Inspection Queue's
"Supervisor Reviews" bucket at `/inspection-work-queue`, and the
per-inspection `ReadinessDispositionPanel`/disposition-action endpoints
from v1.6) — this page just predates that work and was never reconnected
or removed.

**Fix**: redirect `/findings` to `/inspection-work-queue` (or rewire this
page to pull the real `supervisor_reviews` bucket from
`GET /api/inspection-work-queue`) so both nav entries lead to real,
actionable data.

### 2. `/operations` ("Operational Analytics" nav link) is explicitly labeled sample data

`frontend/src/pages/OperationsDashboard.tsx` literally reads
*"Pilot-safe sample activity for daily review"* in its own UI copy — an
acknowledged placeholder, never wired to a real endpoint. Same nav-mismatch
problem as above: a manager clicking "Operational Analytics" sees
permanent fake numbers.

**Fix**: redirect `/operations` to the real v1.7
`/api/workflow/analytics` + `/api/workflow/daily-dashboard` data (or point
the nav entry directly at a page backed by them), since that's the
non-fabricated equivalent already built.

## Moderate

### 3. Inconsistent error-handling coverage across pages

- `Dashboard.tsx` (main `/` dashboard): well-hardened — `Promise.allSettled`
  across four endpoints, explicit `loading`/`error`/empty states, partial
  failures degrade individual KPI cards to "—" rather than crashing. No
  action needed.
- `LoginPage.tsx`: has explicit `error`/`loading` state and a `.catch`
  around the failure path. No action needed.
- `NewInspectionPage.tsx`: has `.catch` around its main submission calls
  but not uniformly around every secondary fetch (e.g. anatomy-zone
  lookups) — a secondary lookup failure could leave a section silently
  stuck loading rather than showing an error. Lower severity since the
  primary inspection-submission path is covered.
- `IntakeHistoryPage.tsx` delegates all data-fetching to child components
  (`EnterpriseIntakeHistoryPanel`, `InspectionResultsHistory`) rather than
  fetching itself — those components were not individually audited in this
  pass; flagged for the next iteration.

### 4. Role enforcement (backend) — verified correct

`routes/inspections.py`'s `require_inspection_runner` correctly restricts
inspection creation (image upload + AI analysis) to
`operator`/`spd_manager`/`admin`, rejecting `viewer` with a clear,
actionable 403 (`"Viewer access is read-only. Ask an admin to assign
Operator or SPD Manager access to run inspections."`) rather than a
generic or silent failure. The v1.6/v1.7/v1.8 disposition/override/
teaching-point endpoints all correctly gate on `admin`/`spd_manager` only.
This part of the spec's role matrix is already solid — see
`docs/pilot/pilot-site-configuration.md` for the full matrix as
documented/verified.

## Not yet audited (carried to the next iteration)

- Full click-through of instrument selection, anatomy zone selection, and
  clinical report generation in a live browser session (this pass was a
  static code audit; a live pass is queued).
- `EnterpriseIntakeHistoryPanel` / `InspectionResultsHistory` error
  handling.
- Hard-refresh behavior on deep routes (e.g. reloading directly on
  `/inspection-work-queue`) — `main.tsx`'s chunk-load recovery guard
  (`recoverFromStaleAssets`) already handles the *stale-asset-after-deploy*
  case; a live pilot-network reload test is still queued.
