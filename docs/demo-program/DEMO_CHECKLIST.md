# LumenAI — Demo Checklist

Objectives 16 (Demo Validation) and 13 (Demo Assets) review. This is a literal, actionable checklist — each item is tied to a specific, verified finding elsewhere in this document set or in the Phase 1/3/4 review documents, not a generic "make sure it works" template.

## Objective 16 — Demo validation checklist

- [ ] **Every workflow completes successfully** — rehearse the Technician flow (`/inspection/new`) end-to-end immediately before any live demo; confirm the inline `AIPredictionPanel` renders real findings rather than an error state.
- [ ] **Every AI explanation is understandable** — confirm the disposition `explanation` text is rendering in `ReadinessDispositionPanel.tsx` (real and working, per `docs/ux-review/UX_GUIDELINES.md`) rather than a bare label. Do **not** promise a visual bounding-box/heatmap overlay — this does not exist anywhere in the codebase and should not be improvised live.
- [ ] **Every dashboard loads correctly** — for any dashboard featured in a demo script, confirm it is rendering real seeded data, not a silent hardcoded fallback. `ROICenterPage.tsx` and `ValueRealizationPage.tsx` both have a silent fallback to fabricated numbers on API failure with no visible indicator — explicitly check the network tab or API logs before a live investor/executive demo to confirm the real data path is active.
- [ ] **Every synthetic dataset is realistic** — confirm `seed_pilot_data.py` has been re-run before the demo session (deterministic `random.Random(42)` seed makes rehearsal and live demo identical). Do not rely on stale data from a prior demo session.
- [ ] **Every user role has a complete experience** — cross-check against `docs/demo-program/ROLE_BASED_DEMOS.md`'s per-persona honesty notes; four personas (Infection Prevention, OR Leadership, Quality Department, Research Partner) have no purpose-built screen and must be scripted as guided tours of existing dashboards, not presented as dedicated role experiences.
- [ ] **No broken navigation** — 45 of ~90 routes have no sidebar entry (`docs/ux-review/NAVIGATION_ARCHITECTURE.md`). Any demo beat that requires one of these screens (`/council`, `/maestro`, `/executive`, `/strategy`, `/veritas`, `/steward`, `/instrument-forensics`, `/risk`, etc.) must be rehearsed via direct URL entry — do not assume the presenter can reach it by clicking through the sidebar without practice.
- [ ] **No missing assets** — see the asset inventory below.

## Objective 13 — Demo assets inventory (what's real vs. what needs to be produced)

| Asset | Status | Notes |
|---|---|---|
| Presentation deck | **Needs to be produced** | No slide deck file exists in this repository; `docs/demo-program/EXECUTIVE_PRESENTATION.md` and `INVESTOR_PRESENTATION.md` provide the narrative content to build one from |
| Architecture diagrams | **Real, exists** | `docs/architecture/` (16 files) contains substantive technical/clinical architecture documentation; `docs/adr/` has 9 real ADRs from the Phase 1 review |
| Workflow diagrams | **Partial** | Text-based workflow descriptions exist throughout `docs/pilot/`, `docs/customer/`, and this document set; no polished visual workflow diagram assets were found — text diagrams would need to be converted to visual form for a deck |
| System screenshots | **Needs to be produced** | No screenshot assets exist in this repository; must be captured live from a seeded demo environment (see `docs/demo-program/SYNTHETIC_DATA_GUIDE.md` for what to seed first) |
| Demo videos | **Not present** | No video assets exist in this repository |
| Clinical validation summary | **Real, exists** | `docs/clinical-validation/` (11 files from Phase 3) — cite `CLINICAL_READINESS_SCORECARD.md` directly rather than re-summarizing |
| Security overview | **Real, exists** | `docs/production-readiness/` (Phase 1) covers audit logging, secrets handling, tenant isolation, CORS, and the 3 genuine Critical Gaps (TD-16 dev-auth risk, TD-09 mock-dashboard risk, TD-02/17/18 database integrity) — any security overview produced for this program must disclose these Critical Gaps, not omit them |
| Product roadmap | **Real, exists** | `docs/roadmap/PHASE_3_PRODUCT_HARDENING_ROADMAP.md` gives an honest current-state-vs-target-state framing and should anchor any roadmap slide |

## Demo-image asset gap — carried forward from SYNTHETIC_DATA_GUIDE.md

The demo image library (`pilotImageManifest.ts`, 20 entries, all `available: false`; `frontend/public/demo-images/lumened-instruments/`, 4 SVG placeholders only) is not populated with real content. **Any "system screenshot" or demo-video asset produced under this program will need to work around this gap** — either capture screenshots showing the placeholder-state UI honestly, or arrange for real/licensed instrument photography before producing polished visual assets. Do not present the manifest's fictional 20-entry metadata as if it reflects populated content.

## Pre-demo environment checklist (operational, not documentation)

- [ ] Confirm `DEMO_MODE` is enabled only in the isolated demo deployment, never alongside a real tenant (see `docs/demo-program/DEMO_MASTER_PLAN.md`'s dev-token bypass risk).
- [ ] Re-run `backend/scripts/seed_pilot_data.py` and, if the demo includes enterprise-portfolio content, `backend/scripts/seed-demo-data.sh`.
- [ ] Confirm the specific dashboards featured in the chosen demo script (per `docs/demo-program/DEMO_SCRIPT_LIBRARY.md`) render real, non-empty data.
- [ ] Confirm which specialist-chain claims will be made (if any) match the honest Objective-8 framing in `docs/demo-program/ROLE_BASED_DEMOS.md` — rehearse the Council `convene()` flow live if it will be demonstrated, since it requires two prior manual API calls.
