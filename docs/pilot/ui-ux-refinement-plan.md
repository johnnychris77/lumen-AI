# UI/UX Refinement Plan

**Version:** 1.0  
**Phase:** 8 — Pilot Findings Analysis & UI Refinement  
**Date:** 2026-06-23  
**Scope:** LumenAI Pilot — Bon Secours Pilot tenant

---

## 1. Friction Audit Summary

Issues ranked by user impact: **High** = blocks task completion or causes data loss; **Medium** = adds significant navigation overhead; **Low** = polish/convenience.

---

## 2. High-Priority Friction

### H-1 — No Image Upload in Inspection Form (100% task failure)

**Page:** `/inspection/new` (`NewInspectionPage.tsx`)  
**Issue:** Images must be uploaded at a separate page (`/inspection-image-upload`) after the inspection record is submitted. The success screen has no link or prompt to the upload page. In pilot Week 1, 100% of technicians skipped the image upload step.  
**User impact:** 0 inspection images captured. AI scoring cannot use visual features.  
**Recommendation:** Embed an image dropzone as Section 5 "Inspection Images" in `NewInspectionPage.tsx`. At minimum, show a "Upload Images Now" primary button on the success screen that links directly to `/inspection-image-upload?inspection_id={id}`.  
**Effort:** 1 day (full embed) or 2 hours (success-screen redirect)

---

### H-2 — Risk Score Not Shown After Submission

**Page:** `/inspection/new` (success state)  
**Issue:** After submitting an inspection, the technician sees a success toast but no computed risk score. The form resets. The technician must navigate to Intake History to see the risk score.  
**User impact:** Technicians have no immediate feedback on the severity of what they just submitted. High-risk findings are not actioned quickly.  
**Recommendation:** Display the computed `risk_score` and `risk_level` badge in the success state before the form resets. Example: "Inspection submitted — Risk Score: **72 / High**."  
**Effort:** Half day

---

### H-3 — Five Finding Categories Return Risk Score 0 (Scoring Bug)

**File:** `backend/app/analytics/risk_engine.py`  
**Issue:** `calculate_risk()` only handles `debris`, `stain`, and `corrosion`. Blood, bone, tissue, crack, and insulation_damage all return 0.  
**User impact:** A cracked ureteroscope inspection scores 0 — indistinguishable from a clean instrument. SPD Managers acting on risk scores receive wrong clinical signal for 34% of findings.  
**Recommendation:** Expand `calculate_risk()` to include all 7 finding categories with clinically-appropriate base scores (see `pilot-findings-analysis.md` § 7c).  
**Effort:** 1 hour

---

### H-4 — Facility / Department / Tray Not Persisted

**File:** `backend/app/models/*.py` (Inspection ORM)  
**Issue:** `facility_name`, `department`, and `tray_id` are sent in the inspection POST payload but not saved as separate columns. They are merged into `vendor_name` / `site_name` / `file_name` fields.  
**User impact:** Tray-level, department-level, and facility-level reporting is impossible from the database. These are required for SPD Manager analytics.  
**Recommendation:** Add columns to `Inspection` model and generate a migration. Update the intake route to persist them.  
**Effort:** 1 day (schema + migration + route + form validation)

---

## 3. Medium-Priority Friction

### M-1 — No Instrument Passport Deeplink from Intake History

**Page:** `/intake-history` (`IntakeHistoryPage.tsx` → `EnterpriseIntakeHistoryPanel`)  
**Issue:** After reviewing an inspection record, the SPD Manager must navigate to `/infrastructure`, click the Passport tab, and manually re-select the instrument from a dropdown. There is no direct "View Passport" link from the inspection row.  
**Recommendation:** Add a "Passport" action button (or icon link) on each inspection row that navigates to `/infrastructure?tab=passport&instrument={barcode}`. Add query param handling in `GlobalInfrastructureConsole.tsx` to pre-select the instrument.  
**Effort:** 2 hours

---

### M-2 — Baseline Review Queue Has No Priority Sort

**Page:** `/baseline-review` (`BaselineReviewPage.tsx` → `BaselineReviewQueue`)  
**Issue:** Baselines appear in creation order. Reviewers cannot tell which baselines are blocking live inspections.  
**Recommendation:** Add a "Blocking N inspections" badge per baseline card computed from the count of uninspected instruments in that category. Sort by blocking count descending by default.  
**Effort:** Half day

---

### M-3 — No "No Approved Baseline" Warning on Inspection Form

**Page:** `/inspection/new`  
**Issue:** When a technician selects an `instrument_type` for which no approved baseline exists, no warning is shown. The risk score will have a reduced baseline component (silently 0 currently due to H-3).  
**Recommendation:** On `instrument_type` change, fetch `/api/baseline-library?instrument_category={type}&status=approved` and display a non-blocking amber alert: *"No approved baseline found for this instrument type — risk score accuracy may be reduced."*  
**Effort:** 2 hours

---

### M-4 — No Validation Error Scroll-to-First-Error

**Pages:** All forms (`NewInspectionPage.tsx`, `BaselineImageUploadPage.tsx`, `InspectionImageUploadPage.tsx`, vendor forms)  
**Issue:** When a form is submitted with validation errors, the first errored field is not scrolled into view. On mobile (single-column layout), the user may not see which field is errored.  
**Recommendation:** On submit, find the first element with a validation error state and call `.scrollIntoView({ behavior: "smooth", block: "center" })`.  
**Effort:** 2 hours (shared utility function applied to all forms)

---

### M-5 — Instrument Type Options Include Non-Lumened Instruments

**Page:** `/inspection/new` — Section 3 "Instrument Identification"  
**Issue:** `instrument_type` select includes `scissors`, `forceps`, `clamp`, `needle_holder`, `retractor`, `scalpel_handle`, and `drill` — none of which are lumened instruments. The pilot fleet is all lumened scopes.  
**Recommendation:** Reorder options to put lumened types first: `scope`, `flexible_ureteroscope`, `bronchoscope`, `colonoscope`, `hysteroscope`, `cystoscope`, `arthroscope`, `nephroscope`, then `other`. Relabel generic "scope" to "Other Scope / Lumened Instrument."  
**Effort:** 1 hour

---

### M-6 — BaselineLibraryPage Is a Stub

**Page:** `/baseline-library`  
**Issue:** The page shows a placeholder with two navigation buttons. There is no searchable baseline catalogue, no filtering by category or status, and no way to view a baseline record without going through the review queue.  
**Recommendation:** For Sprint 7, at minimum render the approved baseline list fetched from `/api/baseline-library?status=approved`. Display: instrument category, manufacturer, model, type, approved date. Search by keyword. Full advanced filtering in Sprint 8.  
**Effort:** 1 day (basic searchable list)

---

### M-7 — Dashboard Image Library KPI Group Contains Duplicates

**Page:** `/` (Dashboard)  
**Issue:** The "Image Library KPIs" group shows three cards: "Demo Image Cards," "Approved + Pending Baselines" (duplicate of Pilot KPIs), and "Approved Baselines" (duplicate). Two of three KPIs are the same numbers shown 20 pixels away.  
**Recommendation:** Remove the "Image Library KPIs" section entirely or replace with genuinely distinct KPIs: images uploaded this week, image upload success rate, inspections with 0 images attached.  
**Effort:** 1 hour

---

### M-8 — No Tenant Filter on Dashboard

**Page:** `/`  
**Issue:** All KPI cards show aggregate data with no tenant scoping. When a second facility is onboarded, Bon Secours SPD staff will see combined metrics.  
**Recommendation:** Add a tenant filter dropdown (or scope KPI API responses by the authenticated user's tenant_id) before second-facility rollout.  
**Effort:** Half day (API already tenant-scoped; add UI filter)

---

## 4. Low-Priority Friction

### L-1 — Mobile Layout: New Inspection Form Is Single-Column

**Page:** `/inspection/new`  
**Issue:** All 15+ fields render in a single column on mobile, requiring excessive vertical scrolling.  
**Recommendation:** Add `sm:grid-cols-2` for the Instrument Identification section fields (manufacturer/model/serial/barcode/QR/UDI/KeyDot). Site Info and Findings sections can remain single-column.  
**Effort:** 2 hours (CSS only)

---

### L-2 — Barcode Field Has No Scanner Feedback

**Page:** `/inspection/new` — Section 3 Instrument ID  
**Issue:** Barcode field accepts text input and works with USB HID Zebra scanners (keyboard emulation), but there is no visual confirmation of scan capture, no auto-advance to next field, and no auto-populate of instrument details from the registry.  
**Recommendation (Sprint 7):** On barcode field blur (after scanner input), show a brief green "Scanned ✓" indicator. On Sprint 8: fetch instrument details from registry and auto-fill manufacturer, model, and instrument_type.  
**Effort:** 2 hours (visual feedback) + 1 day (auto-fill from registry)

---

### L-3 — Upload Pages Lack Guidance

**Pages:** `/baseline-image-upload`, `/inspection-image-upload`  
**Issue:** Upload pages show a dropzone with no guidance on resolution, file size, PHI warning, or naming convention.  
**Recommendation:** Add a collapsible "Capture Guidelines" section above the dropzone with: minimum resolution, maximum file size, required angles, PHI warning, naming convention example.  
**Effort:** 2 hours

---

### L-4 — CAPA Queue Doesn't Show Source Instrument

**Page:** `/capa`  
**Issue:** CAPA records show the CAPA type and status but not which instrument triggered the CAPA event.  
**Recommendation:** Add `instrument_type` and `barcode` columns to the CAPA list table, linked to the Instrument Passport.  
**Effort:** 2 hours

---

### L-5 — Finding Category Tooltips Missing

**Page:** `/inspection/new` — Section 4 Findings  
**Issue:** The 7 finding category checkboxes have no explanatory tooltips. SPD Educator requested: "What's the difference between debris and tissue?"  
**Recommendation:** Add a `?` icon next to each finding category label. On hover/tap, show a one-line definition.

| Category | Tooltip |
|----------|---------|
| Blood | Visible blood residue in lumen or on instrument surface |
| Bone | Calcified tissue or bone fragment visible in channel |
| Tissue | Soft tissue or protein residue visible in lumen |
| Debris / Bioburden | Non-specific particulate, organic matter, or buildup |
| Corrosion | Rust, pitting, or surface degradation of metal |
| Crack / Fracture | Visible structural break, fracture, or delamination |
| Insulation Damage | Damage to electrical insulation on monopolar/bipolar instruments |

**Effort:** 2 hours

---

### L-6 — Vendor Baseline Submission Has No Status Visibility

**Page:** `/vendor-baseline-portal` or `/vendor-intake`  
**Issue:** After submission, vendors receive no confirmation and cannot check submission status.  
**Recommendation:** (a) Show a success toast with a submission ID; (b) add a "My Submissions" section showing the vendor's pending/approved/rejected baselines; (c) Sprint 8: send a confirmation email.  
**Effort:** Half day (UI status page) + 1 day (email)

---

## 5. Friction Priority Matrix

| ID | Issue | Priority | Effort | Recommended Sprint |
|----|-------|----------|--------|--------------------|
| H-3 | Risk score 0 for 5 finding categories | High | 1 hour | Sprint 7 (Now) |
| H-1 | No image upload in inspection form | High | 1 day | Sprint 7 |
| H-2 | Risk score not shown post-submission | High | Half day | Sprint 7 |
| H-4 | Facility/dept/tray not persisted | High | 1 day | Sprint 7 |
| M-1 | No Passport deeplink from Intake History | Medium | 2 hours | Sprint 7 |
| M-2 | Baseline review queue no priority sort | Medium | Half day | Sprint 7 |
| M-3 | No "no baseline" warning on form | Medium | 2 hours | Sprint 7 |
| M-4 | No scroll-to-error on form submit | Medium | 2 hours | Sprint 7 |
| M-5 | Instrument type includes non-lumened options | Medium | 1 hour | Sprint 7 |
| M-7 | Dashboard Image Library KPIs duplicated | Medium | 1 hour | Sprint 7 |
| M-6 | BaselineLibraryPage is a stub | Medium | 1 day | Sprint 8 |
| M-8 | No tenant filter on dashboard | Medium | Half day | Sprint 8 |
| L-1 | Mobile single-column layout | Low | 2 hours | Sprint 7 |
| L-2 | Barcode field no scanner feedback | Low | 2 hours | Sprint 7 |
| L-3 | Upload pages lack guidance | Low | 2 hours | Sprint 7 |
| L-4 | CAPA queue no source instrument | Low | 2 hours | Sprint 8 |
| L-5 | Finding category tooltips missing | Low | 2 hours | Sprint 8 |
| L-6 | Vendor baseline no status visibility | Low | Half day + 1 day | Sprint 8 |

---

## 6. Accessibility Baseline

| Check | Status | Note |
|-------|--------|------|
| All form inputs have `<label>` or `aria-label` | ✅ | Confirmed in NewInspectionPage.tsx |
| Color is not the only finding indicator | ✅ | Badge text + color |
| Upload dropzone keyboard accessible | ✅ | `<input type="file">` pattern |
| Error messages linked to inputs by `id`/`aria-describedby` | ⚠️ | Not confirmed — Sprint 7 check |
| Screen reader support for KPI cards | ⚠️ | Cards use `aria-hidden` icons but lack `aria-label` on value |

---

*LumenAI Pilot Program — Internal Use Only*  
*Focus of this document is usability and adoption — all security controls and auditability mechanisms remain unchanged.*  
*LumenAI makes no claim of FDA clearance or regulatory approval.*
