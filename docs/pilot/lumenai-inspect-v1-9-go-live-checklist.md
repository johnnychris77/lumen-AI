# LumenAI Inspect v1.9 — Pilot Go-Live Checklist

Use this checklist before allowing real inspection data at the first
pilot site. Every item should be verifiable — check it against a real
screen or a real API response, not against intent.

## 1. User Setup

- [ ] At least one `admin` account exists and can log in (`POST /api/auth/login` or the login UI).
- [ ] At least one `spd_manager` account exists per shift/supervisor on staff.
- [ ] At least one `operator` account exists per technician expected to run inspections.
- [ ] Any `viewer` accounts (auditors, leadership observers) are confirmed **read-only** — see Acceptance Test Script, Test Case 3.
- [ ] `ADMIN_BOOTSTRAP_TOKEN` (or equivalent bootstrap secret) has been rotated from any value used during setup/demo and is not shared outside the deployment operator.
- [ ] `ENABLE_DEV_AUTH` is **not** set in the production environment (dev-token auth must never be reachable outside local/test).

## 2. Baseline Setup

- [ ] At least one approved manufacturer baseline exists for every instrument type the pilot site will actually inspect (`GET /api/baselines` or the Manufacturer Baselines page).
- [ ] `PilotSiteConfig.baseline_required` reflects the site's real policy (default `true` — an inspection without a baseline routes to supervisor review, it is never silently scored).
- [ ] Vendor baseline submission workflow tested end-to-end at least once if the site uses vendor-submitted baselines.

## 3. Instrument Setup

- [ ] `PilotSiteConfig.enabled_instrument_families` set to the families this site actually processes (`PUT /api/pilot-deployment/site-config`, admin only).
- [ ] Anatomy zone requirements for each enabled family reviewed with SPD leadership (`GET /api/knowledge/competency-topics` and the Anatomy Library page).
- [ ] `PilotSiteConfig.minimum_coverage_pct` set to the site's real coverage policy (default 75%).

## 4. Role Setup

- [ ] Verified against the Acceptance Test Script: viewer cannot create an inspection, cannot upload, cannot run AI analysis, cannot approve a disposition.
- [ ] Verified: operator can create an inspection, upload an image, and see the AI analysis result.
- [ ] Verified: spd_manager can review, override, approve, add a teaching point, and finalize a disposition.
- [ ] Verified: admin can manage users, baselines, and pilot site configuration.

## 5. Image Capture Workflow

- [ ] A technician has completed at least one real (non-demo) inspection end-to-end: instrument selection → anatomy zone tagging → image upload → AI analysis result displayed.
- [ ] `GET /api/inspections/{id}/data-quality` reviewed for that inspection — confirm no unexpected guardrail failures for a normal, well-captured inspection.
- [ ] Borescope/device-key capture station workflow (`/station`) tested if the site uses shared capture hardware.

## 6. Supervisor Review Workflow

- [ ] A supervisor has completed at least one real disposition action (`POST /api/inspections/{id}/disposition-action`) — approve, and at least one override (reclean/repair/escalate).
- [ ] The Smart Inspection Queue (`/inspection-work-queue`) and Findings Queue (`/findings`) both show the same real pending inspection — confirms the two pages are not showing divergent data.
- [ ] A supervisor has captured at least one teaching point (`POST /api/inspections/{id}/teaching-point`) and confirmed it appears in the Knowledge Center.

## 7. Daily Support Process

- [ ] A named on-call contact (with phone/pager or equivalent) is documented for the first two weeks of pilot use.
- [ ] `GET /api/pilot-deployment/data-collection` is checked daily by the pilot lead during the first two weeks — incomplete inspections and failed uploads reviewed same-day.
- [ ] `GET /api/pilot-deployment/site-config` reviewed weekly to confirm thresholds still match the site's operating reality.

## 8. Escalation Path

- [ ] Critical/high-risk findings (`risk_tier` Critical or High Risk in the Smart Inspection Queue) have a documented same-shift escalation path to a supervisor.
- [ ] A `report_generation_failure` or repeated `upload_failure`/`ai_analysis_failure` in the error log (`app.services.pilot_error_log_service.error_summary`) triggers a support ticket, not silent retry-and-hope.
- [ ] A path exists to reach the engineering team directly if the daily data-collection dashboard shows a sustained spike in incomplete inspections.

## 9. Go/No-Go Criteria

Go live only when **all** of the following are true:

- [ ] Full backend test suite passes (`PYTHONPATH=. python -m pytest tests -q`) with zero unexpected failures.
- [ ] `ruff check backend/app backend/tests` passes clean.
- [ ] `npm --prefix frontend run build` succeeds clean.
- [ ] At least one technician and one supervisor have each completed a real end-to-end workflow pass (see Acceptance Test Script).
- [ ] A viewer account has been confirmed read-only.
- [ ] The Pilot Data Collection Dashboard is reachable and shows zero unexplained `failed_uploads`.
- [ ] The named on-call contact and escalation path are documented and communicated to the pilot site's staff.

If any Go/No-Go item is not met, treat it as a blocker — do not go live
on a partial pass.
