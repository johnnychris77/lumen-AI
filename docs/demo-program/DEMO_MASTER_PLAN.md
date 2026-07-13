# LumenAI — Demo Master Plan

**Launch Readiness Program · Phase 5: Showtime · Production Demonstration, Pilot Readiness & Customer Experience**

Objective 1 (Demo Environment), plus the demo-dashboard (Objective 10), demo-data (Objective 11), and demo-validation (Objective 16) threads that tie the whole program together. This plan is grounded in what already exists in this repository, not an idealized target — where a requirement (e.g. "synthetic Digital Twins") is only partially real today, that's stated plainly, consistent with the discipline established across Phases 1, 3, and 4.

## What a demo environment actually is today

There is no single "demo environment" switch — it is several independent, real pieces:

1. **`DEMO_MODE=1`** (`backend/app/routes/demo.py`) gates one endpoint, `GET /api/demo/reset`, which clears `PilotStatus`/`TenantUsageCounter` rows for `tenant_id in ("demo", "default-tenant")`.
2. **`backend/scripts/seed_pilot_data.py`** — a real, runnable, deterministic (`random.Random(42)`) generator producing 10 hand-authored instrument records, 25 baseline library entries, and 50 inspection records with a hand-tuned finding distribution. This is the actual clinical-data seed.
3. **`backend/scripts/seed-demo-data.sh`** — hits live API endpoints to seed 5 named demo enterprise tenants (Northstar Surgical Network, MetroCare System, Riverside Health, Summit Specialty Partners, Atlantic Care Alliance) with hand-authored portfolio/health/risk attributes.
4. **`scripts/seed_enterprise_investor_demo.sh`** and **`scripts/public-demo-go-live.sh`** (+ related rollback/check scripts) — operate against a hosted Render backend for investor/public demo scenarios.
5. **`docs/commercial/demo-environment-guide.md`** — the existing sales-engineer runbook; states plainly "No PHI, ever. Demos use synthetic/seeded data only" and gives real `uvicorn`/env-var commands.

**A known security risk carried into this plan**: `demo.py`'s auth check accepts either `Bearer demo-token` or `Bearer dev-token` whenever `DEMO_MODE=1` — the same static `dev-token` string that appears throughout the repo's dev scripts. This is a real bypass path, not hypothetical, and mirrors TD-16 in `docs/production-readiness/PRODUCTION_READINESS_SCORECARD.md`. **`DEMO_MODE` must never be enabled outside an isolated demo deployment**, and this constraint should be stated on every demo-environment runbook produced under this program.

## Requirement-by-requirement reality check

| Requirement | Status | Basis |
|---|---|---|
| Synthetic clinical data | **Real** | `seed_pilot_data.py` (10 instruments, 25 baselines, 50 inspections, deterministic) |
| Synthetic hospitals | **Real** | `seed-demo-data.sh`'s 5 named enterprise tenants; `docs/demo/executive-demo-walkthrough.md`'s "Bon Secours (demo tenant)" |
| Synthetic technicians | **Partial** | Instrument/inspection records reference technician identifiers, but no dedicated synthetic-technician-roster generator exists separately |
| Synthetic instruments | **Real** | `seed_pilot_data.py`'s 10 hand-authored instrument records |
| Synthetic Digital Twins | **Split** | `digital_quality_twin_service.py` has a genuine seeded-mock fallback (`hashlib.md5` → `random.Random`, explicit comment: *"Use seeded mock for scores (real scoring engine would require ML model)"*) used across forecasts/scenarios/interventions/exec-briefs. `apollo_quality_twin_service.py` has **no seed/demo path at all** — it deliberately refuses to fabricate department-level splits it can't support with real data, and needs genuine inspection/accreditation history to populate meaningfully. A demo relying on Apollo's twin needs real seeded inspection volume behind it first. |
| Synthetic inspection history | **Real, but smaller than marketing copy claims** | `seed_pilot_data.py` produces 50 inspections; `docs/demo/executive-demo-walkthrough.md` claims "~2,847 seeded inspections" — **this figure does not match any generator found in the codebase** and should be corrected in this program's materials rather than repeated. |
| Synthetic dashboards | **Real** (see [DASHBOARD_STANDARDS.md](../ux-review/DASHBOARD_STANDARDS.md) for the full 68-dashboard inventory) | Dashboards render whatever data is seeded — they are real components, not demo-only mockups |
| No production or PHI data | **Enforced by construction, not by a content scanner** | See "PHI guardrail reality" below |

## PHI guardrail reality — narrower than the policy language implies

A real, if narrow, technical guardrail exists: `backend/app/routes/integrations.py`'s `_PHI_FORBIDDEN` field-name blocklist (`patient_id`, `mrn`, `dob`, `patient_name`, `name`, `ssn`) strips those keys from incoming event dicts before processing, duplicated in `spd_connectors.py`'s `PHI_PROHIBITED` set. Beyond that, PHI-freedom is enforced by **construction** (the seed generators simply never include patient fields) and by **human self-attestation** (`no_phi_confirmed` boolean flags in `olympus_exchange_service.py`/`genesis_ai_intelligence_cloud.py`, `phi_review_status` in `sage_image_library_service.py`) — there is no runtime content scanner that would catch PHI if someone accidentally injected it into a free-text field or image. **This program's demo materials should state the guardrail accurately**: "no PHI by design and by convention, with a narrow field-name blocklist on ingestion — not a comprehensive automated PHI scanner."

## The demo image library is a scaffold, not a populated library

`frontend/src/data/pilotImageManifest.ts` has 20 hand-authored metadata entries (baseline/inspection/borescope/finding categories) — **all 20 are marked `available: false`**, and `frontend/public/demo-images/lumened-instruments/` contains only 4 SVG placeholder files. `DemoImageLibraryPage.tsx` itself displays a "No real pilot images are loaded yet" banner when `summary.available === 0`. The executive-demo-walkthrough's claim of "120 demo images" does not match this. **Any demo program deliverable referencing example instrument images must either use the 4 real placeholder SVGs, or flag real photography as an outstanding pre-demo task** — do not present the manifest's 20 fictional entries as populated content.

## Demo dashboards (Objective 10)

No new dashboards need to be built — [DASHBOARD_STANDARDS.md](../ux-review/DASHBOARD_STANDARDS.md) already inventories 68 real dashboard pages. The demo program's job is to **select and polish**, not construct: choose the specific dashboards each role-based demo (see [ROLE_BASED_DEMOS.md](./ROLE_BASED_DEMOS.md)) will walk through, and confirm each one has enough seeded data behind it to render meaningfully rather than an empty state. Given the redundant-KPI finding in that same document (Total Inspections/Critical Findings/Pass Rate recomputed inconsistently across 3-8 screens each), **pick one canonical dashboard per KPI for the demo script** rather than switching between near-duplicates mid-demo, which would visibly expose the inconsistency to an audience.

## Demo validation (Objective 16) — a literal checklist, not prose

Moved to [DEMO_CHECKLIST.md](./DEMO_CHECKLIST.md), which operationalizes this objective's 7 bullet points against the specific gaps this recon found (e.g. "no broken navigation" must specifically re-check the 45 orphaned routes from [NAVIGATION_ARCHITECTURE.md](../ux-review/NAVIGATION_ARCHITECTURE.md) that a demo script might stumble into).

## Recommendation

Before any live demonstration under this program:
1. Confirm `DEMO_MODE` is enabled only in an isolated deployment, never alongside a real tenant.
2. Re-seed with `seed_pilot_data.py` immediately before each demo session (its `random.Random(42)` seed makes output reproducible, so rehearsal and the live demo will show identical data).
3. Correct the "~2,847 inspections" / "120 images" figures in existing demo collateral to match what the generators actually produce, or expand the generators to match the claim — do not present the current mismatch to an external audience.
4. Treat Apollo's twin as **not demo-ready** until enough real seeded inspection/accreditation history exists behind it; lead twin demonstrations with `digital_quality_twin_service.py`'s forecast/scenario/intervention views instead, which have a genuine synthetic-data path.
