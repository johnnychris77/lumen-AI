# Pilot Lessons Learned

**Version:** 1.0  
**Phase:** 7 — Pilot Site Deployment  
**Covering:** Phases 1–7 implementation + Pilot Week 1 deployment  
**Date:** 2026-06-23

---

## 1. Executive Summary

LumenAI's Phase 1–7 build achieved a functional, security-hardened pilot platform covering instrument registration, baseline workflows, inspection intake, image management, and an Instrument Passport. The platform is CONDITIONAL GO for wider rollout. This document captures friction points, gaps, and improvements identified during build and pilot deployment that should feed the Sprint 7–9 backlog.

---

## 2. Workflow Friction

### 2a. Baseline-Before-Inspection Dependency Is Not Enforced

**Observation:** The AI scoring baseline component (20% of risk score) silently returns 0 when no approved baseline exists for the submitted instrument type. Users receive no warning.

**Impact:** SPD staff submitting inspections before baselines are approved will see deflated risk scores with no explanation. Pilot educators flagged this as confusing.

**Recommendation:** Add a soft warning on `/inspection/new` when no approved baseline exists for the selected instrument type: *"No approved baseline found for this instrument — risk score accuracy may be reduced."* Non-blocking.

---

### 2b. Two-Step Inspection Image Upload Breaks Mobile Flow

**Observation:** The inspection workflow requires: (1) submit inspection record at `/inspection/new`, then (2) separately upload images at `/inspection-image-upload`. SPD staff expected images to be uploaded in a single step.

**Impact:** Some technicians submitted inspections without images, then couldn't easily locate the upload page.

**Recommendation:** Embed the image dropzone directly in `/inspection/new` as Section 5, or add a "Upload Images Now" button/redirect at the success state of the inspection form. Single-form flow preferred.

---

### 2c. Baseline Review Queue Has No Priority Sort

**Observation:** The baseline review queue at `/baseline-review` shows records in creation order. Reviewers must manually identify which baselines are blocking live inspections.

**Impact:** Pending vendor baselines for frequently-used instruments (ureteroscopes, laparoscopes) sat in the queue behind rarely-used instrument baselines.

**Recommendation:** Add a priority column that surfaces baselines for instruments with pending inspections first. Alternatively, add a "Blocking N inspections" badge on each review card.

---

### 2d. Instrument Passport Requires Manual Instrument Selection

**Observation:** The Passport tab on the Infrastructure Console requires the user to select an instrument from a dropdown each time. There is no deeplink from the inspection record or intake history to the specific instrument's passport.

**Impact:** After reviewing an inspection finding, the SPD Manager wanted to immediately view the instrument's full history — this required navigating to Infrastructure, selecting the Passport tab, and re-selecting the instrument.

**Recommendation:** Add a "View Passport" link on each inspection record in Intake History, passing the instrument barcode or UDI as a query parameter to pre-select it in the Passport view.

---

## 3. UI Improvements

| # | Page | Issue | Recommendation | Priority |
|---|------|-------|----------------|----------|
| UI-1 | New Inspection | Form is single-column on mobile — 15+ fields require excessive scrolling | Add `sm:grid-cols-2` layout for Instrument Details section | Sprint 7 |
| UI-2 | New Inspection | No inline AI risk score after submission | Show computed `risk_score` in success state or redirect to inspection record | Sprint 7 |
| UI-3 | Intake History | No direct link to Instrument Passport from inspection row | Add "Passport" action button with instrument identifier deeplink | Sprint 7 |
| UI-4 | Baseline Review | No indication of how many inspections are blocked by each pending baseline | Add "Blocking N inspections" badge | Sprint 8 |
| UI-5 | Demo Image Library | Upload button missing — must edit manifest manually | Add upload form directly in Image Library page | Sprint 8 |
| UI-6 | Dashboard | KPI cards don't distinguish between pilot tenant data and legacy data | Add tenant filter or "Pilot View" toggle | Sprint 7 |
| UI-7 | All forms | Validation errors don't scroll to the first errored field | `document.querySelector('[data-error]')?.scrollIntoView()` on submit | Sprint 7 |
| UI-8 | Infrastructure | Quality Registry tab has no link back to specific instrument Passport | Add "View Passport" action per row | Sprint 8 |

---

## 4. Missing Fields

| # | Location | Missing Field | Impact | Sprint |
|---|---------|---------------|--------|--------|
| F-1 | `Inspection` ORM model | `facility_name`, `department`, `tray_id` | Captured in form but not persisted as columns — breaks reporting by tray | 7 |
| F-2 | `Inspection` ORM model | `instrument_barcode`, `instrument_udi` | Can't link inspection record to instrument identity without manual lookup | 7 |
| F-3 | New Inspection form | `tray_id` dropdown (vs free text) | Staff are entering inconsistent tray names — affects grouping in analytics | 7 |
| F-4 | Baseline Library | `baseline_image_url` | All 25 seeded baselines have no image attached — reduces visual review usefulness | Now |
| F-5 | Inspection record | `borescope_image_count` | Counted in upload step but not persisted on inspection row | 8 |
| F-6 | Instrument Identity | `last_reprocessing_date` | Needed for cycle-count-based retirement alerts | 8 |
| F-7 | Inspection → Passport | `related_instrument_id` FK | No formal FK between inspection and instrument identity tables | 7 |

---

## 5. Missing Reports

| # | Report | Current Workaround | Recommendation |
|---|--------|-------------------|----------------|
| R-1 | Tray-level contamination summary | Not available | Add tray grouping to analytics dashboard |
| R-2 | Instrument reprocessing history (cycles per instrument) | Passport shows events but no aggregate cycle count trend | Add cycle trend chart to Passport tab |
| R-3 | Baseline coverage report (% of active instruments with approved baselines) | Manual count | Add KPI card to Dashboard |
| R-4 | Review turnaround time report | Not available | Add to Pilot Analytics page |
| R-5 | Upload failure log | Not tracked | Add failed upload audit events |
| R-6 | Finding frequency trend (week-over-week) | Bar chart shows totals only | Add time-series trend line to Analytics |
| R-7 | Instrument risk heat map | Not available | Add instrument × finding matrix to Quality Intelligence |

---

## 6. User Feedback Summary

### SPD Technicians (n=2)
- Positive: "The form is easy to follow and reminds me what fields are required."
- Positive: "I like that it shows which finding type I selected with a color badge."
- Friction: "I didn't know I had to upload images separately after submitting."
- Friction: "The barcode field — can I scan directly into it with our Zebra scanner?"
- Request: "Can it auto-fill the instrument type when I scan the barcode?"

### SPD Manager (n=1)
- Positive: "The baseline review queue is exactly what I needed."
- Positive: "Seeing the risk score per inspection helps me prioritize reviews."
- Friction: "I want to see the whole instrument history in one click from the inspection."
- Friction: "The CAPA queue doesn't show which instrument triggered the CAPA."
- Request: "A daily summary email with yesterday's inspection count and any critical findings."

### SPD Educator (n=1)
- Positive: "The Dashboard KPIs are a great teaching tool."
- Friction: "Readonly access means I can't see how forms are filled in — need to shadow a technician."
- Request: "Explainer tooltips on each finding category — what's the difference between debris and tissue?"

### Vendor User (n=1, Aesculap)
- Positive: "Baseline portal is straightforward."
- Friction: "I don't know if my submission was received — no confirmation email."
- Request: "Email receipt when baseline submission is accepted."

---

## 7. Deployment Issues

| # | Issue | Severity | Resolution |
|---|-------|----------|-----------|
| D-1 | `pilotImageManifest.ts` excluded by `.gitignore` (`data/` rule) | High | Fixed in Phase 5 — added `!frontend/src/data/` negation |
| D-2 | 330 test failures due to missing `ENABLE_DEV_AUTH` env var in conftest | High | Fixed — added `os.environ.setdefault` calls in `conftest.py` |
| D-3 | `executive_briefing_dashboard.py` embedded `"dev-token"` fallback in rendered JS | Medium | Fixed in Phase 7 — replaced with `""` |
| D-4 | `ManufacturerPortal` import in `DashboardApp.tsx` after component deletion | Medium | Fixed in Phase 1 |
| D-5 | `NewInspectionPage.tsx` used undefined `token` variable | Medium | Fixed in Phase 4 — replaced with `hdrs["Authorization"]` |
| D-6 | CI `frontend-security-and-build` failing due to missing manifest file | Medium | Fixed in Phase 5 — committed manifest after gitignore fix |
| D-7 | Seed script requires manual `DATABASE_URL` env — no default | Low | Documented; `os.environ.setdefault` added in script |

---

## 8. Pilot Success Metrics — Week 1

| Metric | Target | Achieved | Notes |
|--------|--------|----------|-------|
| Instruments registered | 10 | 10 | ✅ All 10 lumened instruments |
| Baseline records | 25 | 25 | ✅ 16 approved, 9 pending |
| Inspection records | 50 | 50 | ✅ Full finding distribution |
| Approved baselines | ≥ 8 (1 per category) | 16 | ✅ Exceeded target |
| Inspections reviewed | ≥ 70% | 70% (35/50) | ✅ On target |
| Upload success rate (records) | 100% | 100% | ✅ 0 API rejections |
| Image upload success rate | TBD | 0% | ⚠️ Images not yet captured |
| Review turnaround (avg) | < 4 h | ~2 h (simulated) | ✅ Under SLA |
| PHI violations | 0 | 0 | ✅ |
| Security incidents | 0 | 0 | ✅ |
| Critical findings flagged | ≥ 1 | 3 | ✅ Crack + insulation damage |

---

## 9. Go / No-Go for Wider Pilot Rollout

| Criterion | Status | Notes |
|-----------|--------|-------|
| Core workflows functional | ✅ GO | Instrument → Baseline → Inspection → Review |
| 10 instruments registered | ✅ GO | |
| 25 baselines seeded | ✅ GO | 16 approved |
| 50 inspections collected | ✅ GO | |
| Security controls intact | ✅ GO | No PHI, no hardcoded tokens |
| Real images ingested | ⚠️ CONDITIONAL | 0 real images; placeholders in use |
| Inspection → Passport deeplink | ⚠️ CONDITIONAL | Workaround: manual navigation |
| Image upload in single flow | ⚠️ CONDITIONAL | Two-step workaround documented |
| Facility/department/tray persisted | ⚠️ CONDITIONAL | Missing from ORM — Sprint 7 |
| Barcode scanner integration | ❌ NOT YET | Sprint 7–8 |

**Verdict: CONDITIONAL GO for wider pilot rollout**

Ready to onboard a second facility once:
1. Real instrument photographs are ingested at Bon Secours
2. Facility/department/tray columns are added to the Inspection model (Sprint 7)
3. Image upload is consolidated into the inspection form (Sprint 7)

---

## 10. Recommended Sprint 7 Backlog (Priority Order)

| # | Item | Type | Effort |
|---|------|------|--------|
| S7-1 | Add `facility_name`, `department`, `tray_id` to Inspection ORM + migration | Schema | 1 day |
| S7-2 | Add `related_instrument_id` FK to Inspection | Schema | Half day |
| S7-3 | Embed image upload in `/inspection/new` (consolidate two-step flow) | Feature | 1 day |
| S7-4 | Add "No baseline found" warning on inspection form | Feature | 2 hours |
| S7-5 | Add "View Passport" deeplink from Intake History rows | Feature | 2 hours |
| S7-6 | Mobile optimization for New Inspection form | CSS | 2 hours |
| S7-7 | Show AI risk score inline after inspection submission | Feature | Half day |
| S7-8 | Add barcode scanner input support (USB HID keyboard emulation) | Feature | Half day |
| S7-9 | Add uniqueness constraint on `(barcode, tenant_id)` | DB | 1 hour |
| S7-10 | Vendor baseline submission confirmation email | Feature | 1 day |

---

*LumenAI Pilot Program — Internal Use Only*  
*This document is a decision-support tool and operational learning record.*  
*LumenAI makes no claim of FDA clearance or regulatory approval.*  
*All AI outputs require qualified human review before clinical action.*
