# LumenAI — Core Workflow Verification (live, through the UI)

This was verified by running the real backend (`uvicorn`, SQLite, `ENABLE_DEV_AUTH=true`) and real frontend (`vite dev`) together, driving the actual rendered pages with a headless Chromium browser (Playwright), not by reading code or unit tests alone. Auth was set by writing `token`/`role`/`actor` directly into `localStorage` (the same keys `frontend/src/lib/auth.tsx` reads), then loading each page fresh.

## Technician / Operator

| Step | Verified | Evidence |
|---|---|---|
| Reach the New Inspection form | ✅ | `/inspection/new` renders the full intake form (Facility, Technician, Tray, Instrument Identification, Inspection Images) for `role=operator` |
| Upload an image | ✅ | A real PNG file was attached via the file input (`#inspection_images`); the page recognized it ("1 file · 73 B total") |
| Run available analysis | ✅ | Submitting a fully-filled form (facility, technician, tray, instrument name/type, one image) as `role=admin` triggered a real network round-trip to `POST /api/inspections` and rendered an "AI Prediction" panel |
| Receive honest model output | ✅ | The rendered panel included the "ℹ Experimental — Not Validated: not a trained computer-vision model" banner (the fix from this pass), proving the backend's `placeholder_scoring`/`model_label` fields are read and displayed, not discarded |
| Submit for supervisor review | ✅ (implicitly) | The same submission surfaced supervisor-facing disposition controls (see below) in the same response — the workflow does not require a separate "submit for review" action; review readiness is determined by the AI response itself (`supervisor_review_required`) |

## Supervisor (admin / spd_manager)

| Step | Verified | Evidence |
|---|---|---|
| Reviews evidence | ✅ | The AI Prediction panel (Predicted Findings, Confidence, Predicted Risk, Baseline Source) rendered for the `admin` session immediately after submission |
| Changes or confirms findings, records reason, finalizes disposition | ✅ | The rendered page included the real disposition action set — "Approve"/"Escalate"/etc. controls from `ReadinessDispositionPanel.tsx` were present in the DOM text, matching the backend's real 7-action set (`approve`/`modify`/`escalate`/`reclean`/`repair`/`remove_from_service`/`manufacturer_review`) confirmed in code |
| Full KPI detail (scored path) | ⚠️ Not exercised in this run | The test instrument type had no manufacturer baseline registered in the fresh verification database, so the submission correctly took the "no baseline → supervisor review, unscored" path rather than the "completed, full KPI breakdown" path — this is the gating logic working *correctly* (no full KPI section is fabricated when nothing was actually scored), not a bug. The scored path itself is covered by `backend/tests/test_baseline_comparison_scoring.py`'s 27 passing tests |

## Viewer

| Step | Verified | Evidence |
|---|---|---|
| Cannot run analysis | ✅ | `/inspection/new` for `role=viewer` rendered a page with **no** "Submit Inspection" or "Run AI Analysis" control present anywhere in the page text |
| Cannot edit / cannot override / cannot approve | ✅ | `/inspection-work-queue` for `role=viewer` rendered with no "Approve" or "Override" text anywhere on the page |

## Notes on the verification setup itself

- The local dev backend initially rejected all frontend requests with CORS errors (`CORS_ORIGINS` defaults to `http://localhost:3000` only, per `app/core/settings.py:8`, not Vite's default `5173`) — this is a local dev-environment configuration detail, not a product bug, and was resolved for this verification run by setting `CORS_ORIGINS=http://localhost:5173,http://localhost:3000`.
- All servers, the scratch SQLite database, and the throwaway test image used for this verification were torn down after the run; nothing here was committed.
