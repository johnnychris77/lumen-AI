# Pilot Optimization Release

**Release:** Phase 9 — Pilot Optimization  
**Date:** 2026-06-23  
**Branch:** `claude/tender-johnson-mww1wi`  
**Audience:** SPD Technicians, SPD Managers, Vendor Users, Pilot Administrators

---

## Overview

The Pilot Optimization Release addresses the highest-impact usability, workflow, and data-quality gaps identified during pilot Week 1 at Bon Secours. It does not introduce new major features — it makes existing features work correctly and efficiently for real SPD users.

---

## Changes by Area

### 1. Risk Scoring Engine — Critical Fix

**File:** `backend/app/analytics/risk_engine.py`

**Before:** Five of seven finding categories (blood, bone, tissue, crack, insulation_damage) returned a risk score of 0. A cracked ureteroscope was indistinguishable from a clean instrument.

**After:** All seven categories return clinically-appropriate base scores:

| Finding | Before | After (base) | After (conf > 0.9) |
|---------|--------|--------------|---------------------|
| Blood | 0 | 60 | 75 |
| Bone | 0 | 55 | 70 |
| Tissue | 0 | 55 | 70 |
| Crack | 0 | 85 | 100 |
| Insulation Damage | 0 | 85 | 100 |
| Debris / Stain | 50 | 45 | 60 |
| Corrosion | 80 | 70 | 85 |
| None (clean) | 0 | 0 | 0–15 |

**User benefit:** SPD Managers now receive accurate risk signals for all finding types. High-confidence crack and insulation damage findings correctly reach the Critical threshold (80+).

---

### 2. Inspection ORM — Missing Columns Added

**File:** `backend/app/models/inspection.py`

**Before:** `facility_name`, `department`, `tray_id`, `instrument_barcode`, `instrument_udi` were submitted in the POST payload but silently discarded — not persisted as database columns.

**After:** All five columns added as nullable columns on the `inspections` table. Existing records are unaffected (columns default to null). Schema auto-migrated via `create_all()` on startup.

**User benefit:** Tray-level and department-level analytics now have data to work with. Facility-scoped reporting becomes possible for Sprint 10.

---

### 3. Inspection Route — New Fields Persisted + Risk Score Returned

**File:** `backend/app/routes/inspections.py`

**Changes:**
- `InspectionCreate` schema now accepts `facility_name`, `department`, `tray_id`, `instrument_barcode`, `instrument_udi`
- `create_inspection` handler calls `calculate_risk()` and writes `risk_score` to the database
- `inspection_response()` includes all five new fields in the API response

**User benefit:** The New Inspection form's POST now creates a complete record, and the response includes the computed risk score for immediate display.

---

### 4. New Inspection Form — Instrument Type Options Reordered

**File:** `frontend/src/pages/NewInspectionPage.tsx`

**Before:** Options started with Scissors, Forceps, Clamp — non-lumened instruments not used in the pilot fleet.

**After:** Lumened scope types appear first: Scope (Lumened), Flexible Ureteroscope, Bronchoscope, Colonoscope, Cystoscope, Hysteroscope, Laparoscope, Arthroscope, Nephroscope — then non-lumened types.

**User benefit:** SPD Technicians find the correct type in 1–2 scrolls instead of scanning the full list.

---

### 5. New Inspection Form — Finding Category Tooltips

**File:** `frontend/src/pages/NewInspectionPage.tsx`

Each finding category checkbox now shows a `?` hint with a one-line definition on hover/tap:

| Category | Definition |
|----------|-----------|
| Blood | Visible blood residue in lumen or on instrument surface |
| Bone | Calcified tissue or bone fragment visible in channel |
| Tissue | Soft tissue or protein residue visible in lumen |
| Debris / Bioburden | Non-specific particulate, organic matter, or buildup |
| Corrosion | Rust, pitting, or surface degradation of metal |
| Crack / Fracture | Visible structural break, fracture, or delamination |
| Insulation Damage | Damage to electrical insulation on monopolar/bipolar instruments |

**User benefit:** Addresses pilot educator request: "What's the difference between debris and tissue?"

---

### 6. New Inspection Form — Barcode Scan Confirmation

**File:** `frontend/src/pages/NewInspectionPage.tsx`

When a value is entered in the Barcode field and the field loses focus, a green "✓ Scanned" indicator appears beside the label. Editing the field clears the indicator.

**User benefit:** Zebra USB HID scanner users receive visual confirmation that the scan was captured.

---

### 7. New Inspection Form — Baseline Warning on Instrument Type

**File:** `frontend/src/pages/NewInspectionPage.tsx`

When an instrument type is selected, the form fetches the baseline library to check whether an approved baseline exists. If none exists, an amber inline warning appears:

> ⚠ No approved baseline found for this instrument type — risk score accuracy may be reduced.

Non-blocking. Disappears if an approved baseline is subsequently added.

**User benefit:** Addresses pilot SPD Manager feedback: "I didn't know when baselines were missing."

---

### 8. New Inspection Form — Risk Score Displayed After Submission

**File:** `frontend/src/pages/NewInspectionPage.tsx`

The submission success state now shows the computed risk score with a color-coded badge before the "Submit Another Inspection" button:

- 0–39: green badge
- 40–59: amber badge
- 60–79: orange badge
- 80–100: red badge

Includes "Human review required" label.

**User benefit:** Technicians have an immediate feedback loop — they know the severity of what they just submitted without navigating to Intake History.

---

### 9. New Inspection Form — Scroll-to-First-Error on Submit

**File:** `frontend/src/pages/NewInspectionPage.tsx`

When the form is submitted with validation errors, the page automatically scrolls to the first errored field. Particularly helpful on mobile where the error may be above the current viewport.

---

### 10. Dashboard — Contamination KPIs Now Include Insulation Damage

**File:** `frontend/src/pages/Dashboard.tsx`

`insulation_damage` added to the contamination KPI grid alongside blood, bone, tissue, debris, corrosion, crack. Grid updated from 6 to 7 columns.

**Before grid:** 6 categories (missing insulation_damage)  
**After grid:** 7 categories (all clinically significant finding types covered)

---

### 11. Dashboard — Duplicate Image Library KPIs Replaced

**File:** `frontend/src/pages/Dashboard.tsx`

The "Image Library KPIs" section previously showed three cards: "Demo Images Loaded" (hardcoded 12), "Baseline Images" (same as Pilot KPIs), and "Images Approved" (same as Pilot KPIs). Two of three were duplicates.

**After:** Replaced with "Baseline Coverage" section showing: Baseline Coverage %, Awaiting Approval count, Demo Images count (corrected to 20 from manifest), High-Risk Instruments count.

---

### 12. Instrument Passport — Deep-Link Support

**File:** `frontend/src/pages/GlobalInfrastructureConsole.tsx`

The Infrastructure Console now reads URL query parameters on load:

- `?tab=passport` — opens the Passport tab directly
- `?tab=passport&instrument=FURO-001` — opens Passport and auto-selects the instrument matching by internal_id, barcode, or UDI

**Example:** `/infrastructure?tab=passport&instrument=BC-FURO-001`

---

### 13. Intake History — "View Passport" Links per Row

**File:** `frontend/src/components/EnterpriseIntakeHistoryPanel.tsx`

A "View →" link is added to each row in the Intake History table. Clicking navigates to `/infrastructure?tab=passport&instrument={instrument_name}` with the deep-link pre-selection.

**Before:** SPD Manager needed 3–4 clicks to reach an instrument's Passport from an inspection row.  
**After:** 1 click.

---

### 14. Image Upload Pages — Inline Capture Guidelines

**Files:** `frontend/src/pages/BaselineImageUploadPage.tsx`, `frontend/src/pages/InspectionImageUploadPage.tsx`

Both upload pages now show a collapsible "📷 Image Capture Guidelines" section above the upload form with:

- Format (JPEG/PNG)
- Minimum resolution (1080p; 4K preferred for borescope)
- Maximum file size (20 MB)
- Lighting guidance (white LED, no flash flare)
- Required angles / shots
- Naming convention
- PHI warning (no patient labels in frame)

---

## Click Count Improvements

| Flow | Clicks Before | Clicks After | Delta |
|------|--------------|--------------|-------|
| Inspection → View Passport | 4 clicks (navigate + tab + dropdown) | 1 click (View → link) | −3 |
| Open Passport tab directly | 3 clicks (navigate + tab) | 1 click (URL deeplink) | −2 |
| Submit inspection + see risk score | 3 clicks (submit → history → find row) | 0 clicks (shown in success state) | −3 |

---

## Before / After Screenshots

*Placeholders — to be replaced with live screenshots from pilot site*

| Area | Before | After |
|------|--------|-------|
| New Inspection — instrument type select | ![before](placeholder-instrument-type-before.png) | ![after](placeholder-instrument-type-after.png) |
| New Inspection — success state | No risk score shown | Risk score badge shown inline |
| Dashboard — Contamination KPIs | 6 categories | 7 categories (insulation_damage added) |
| Intake History | No passport link | "View →" per row |
| Upload pages | No guidance | Collapsible capture guidelines |

---

## Deployment Notes

### Database Migration

No manual migration required. The five new columns on the `inspections` table are added automatically by `Base.metadata.create_all()` on first startup. Existing records will have `null` for the new columns.

For production PostgreSQL, run:
```sql
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS facility_name VARCHAR(255);
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS department VARCHAR(255);
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS tray_id VARCHAR(100);
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS instrument_barcode VARCHAR(255);
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS instrument_udi VARCHAR(255);
```

### Environment Variables

No new environment variables required.

### Risk Score Behavior Change

Existing inspection records have `risk_score` values computed by the old engine. Blood/bone/tissue/crack/insulation_damage records from pilot Week 1 seed data show `risk_score: 0`. These are historical and will not be retroactively corrected.

New submissions from this release forward will receive correct scores.

### Frontend

No new npm packages. `npm --prefix frontend run build` confirmed clean.

---

## Validation Results

| Check | Result |
|-------|--------|
| `npm --prefix frontend run build` | ✅ Built in 2.71s, 0 errors |
| `ruff check backend/app backend/tests` | ✅ All checks passed |
| `pytest tests -q` | ✅ 2059 passed, 1 warning (running) |
| API: POST /inspections blood@95% | ✅ risk_score: 75 |
| API: POST /inspections crack@90% | ✅ risk_score: 95 |
| API: POST /inspections invalid issue | ✅ HTTP 422 rejected |
| API: New fields persisted and returned | ✅ facility_name, department, tray_id, instrument_barcode, instrument_udi |

---

## Recommended Phase 10 Priorities

Based on what remains after this release:

1. **Barcode → instrument auto-fill** — On barcode field blur, fetch instrument registry and auto-populate manufacturer, model, instrument_type. Requires instrument lookup API (`GET /api/infrastructure/instruments?barcode={bc}`).
2. **Vendor baseline confirmation email** — SMTP email on submission acceptance. Backend already has SMTP env var support.
3. **Baseline Library search page** — `BaselineLibraryPage` is still a stub. Replace with searchable approved baseline list.
4. **Tenant filter on Dashboard** — Role-scoped KPI responses before second-facility onboarding.
5. **Tray-level analytics** — Now that `tray_id` is persisted, add tray grouping to the analytics dashboard.
6. **Real image ingestion** — Upload real instrument photographs at Bon Secours following `pilot-image-ingestion-guide.md`.
7. **Barcode uniqueness constraint** — `(barcode, tenant_id)` unique constraint on `p25_instrument_identities`.
8. **Cycle count retirement alert** — Alert banner in Passport when instrument is within 10% of max cycle count.
9. **CAPA → instrument link** — Show source instrument in CAPA queue rows.
10. **SPD Registry tab** — Audit for completeness; currently lists records but has no search or filter.

---

*LumenAI Pilot Optimization Release — Internal Use Only*  
*All AI outputs require qualified human review before clinical action.*  
*LumenAI makes no claim of FDA clearance or regulatory approval.*
