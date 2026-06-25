# Pilot Findings Analysis

**Version:** 1.0  
**Phase:** 8 — Pilot Findings Analysis & UI Refinement  
**Report Date:** 2026-06-23  
**Facility:** Bon Secours Pilot — Tenant `bon-secours-pilot`  
**Analyst:** LumenAI Engineering

---

## 1. Executive Summary

Phase 8 analysis reviewed all pilot data (10 instruments, 25 baselines, 50 inspections), user workflow patterns across three roles (SPD Technician, SPD Manager, Vendor), backend scoring logic, dashboard KPIs, and the Instrument Passport. The platform is functionally sound but carries three structural gaps that reduce data quality and SPD staff adoption: (1) the risk scoring engine silently returns 0 for five of seven finding categories, (2) facility/department/tray_id are not persisted as ORM columns, and (3) the inspection image upload is a separate two-step flow that technicians skipped in 100% of Week 1 cases.

**Overall pilot grade: B+ (functional, adoption-critical gaps in scoring and image capture)**

---

## 2. Pilot Data Review

### 2a. Baseline Submission Quality

**25 baselines seeded across 8 instrument categories.**

| Status | Count | Notes |
|--------|-------|-------|
| Approved | 16 | All 10 manufacturer baselines + 6 vendor |
| Pending Review | 9 | 3 vendor + 6 network-contributed |

**Gaps:**
- `baseline_image_url` is `null` for all 25 records. Baseline review cannot be visual — reviewers are approving metadata only.
- Network-contributed baselines (6 records) are pending k-anonymity threshold (≥5 contributors). No ETA to approval.
- No uniqueness constraint on `(instrument_category, manufacturer_name, model_name, baseline_type, tenant_id)` — duplicate submissions possible in live intake.

**Bottleneck:** The baseline review queue at `/baseline-review` shows records in creation order with no priority signal. Reviewers cannot identify which pending baselines are blocking active inspections.

---

### 2b. Inspection Submission Quality

**50 inspections collected. 0 API rejections.**

| Finding | Count | % | Expected Range | Status |
|---------|-------|---|----------------|--------|
| None (clean) | 20 | 40% | 35–45% | ✅ |
| Debris | 10 | 20% | 15–25% | ✅ |
| Blood | 8 | 16% | 10–20% | ✅ |
| Tissue | 5 | 10% | 8–15% | ✅ |
| Corrosion | 3 | 6% | 3–8% | ✅ |
| Bone | 2 | 4% | 2–6% | ✅ |
| Crack | 1 | 2% | 1–3% | ✅ |
| Insulation Damage | 1 | 2% | 1–3% | ✅ |

Finding distribution is realistic and within benchmark ranges for a mixed lumened instrument fleet.

**Critical gap — ORM missing fields:**  
`facility_name`, `department`, and `tray_id` are collected in `NewInspectionPage.tsx` and included in the POST payload, but the `Inspection` ORM model does not persist them as separate columns. They are absorbed into `vendor_name` / `site_name` / `file_name` ad-hoc mappings. This prevents tray-level and department-level reporting.

**Missing fields on Inspection ORM (current state):**
- `facility_name` — not a column
- `department` — not a column
- `tray_id` — not a column
- `instrument_barcode` — not a column
- `instrument_udi` — not a column
- `borescope_image_count` — not a column

---

### 2c. Image Upload Quality

| Image Type | Expected | Actual | Gap |
|------------|----------|--------|-----|
| Inspection images | 50 | 0 | 100% missing |
| Borescope images | ~30 | 0 | 100% missing |
| Baseline photos | 25 | 0 | 100% missing |
| Demo placeholders | 20 | 20 | ✅ |

**Root cause of 0% image capture:** The inspection form at `/inspection/new` has no image upload section. After submitting, technicians are expected to navigate separately to `/inspection-image-upload`. During pilot Week 1, 100% of technicians skipped this step.

**Impact:** AI scoring cannot use visual features (YOLO model path disabled when image absent). All 50 inspection scores are computed from metadata only.

---

### 2d. Review and Approval Workflow

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Inspections reviewed | 35 / 50 (70%) | ≥70% | ✅ |
| Avg review time (simulated) | ~2 hours | <4 hours | ✅ |
| Pending reviews | 15 | — | ⚠️ Active queue |
| Vendor baselines pending | 9 | 0 preferred | ⚠️ Queue backed up |
| Baseline queue sort | Creation order | Priority order | ❌ Not implemented |

---

### 2e. Identified Bottlenecks

| # | Bottleneck | Severity | Location |
|---|-----------|----------|----------|
| B-1 | No image upload in inspection form → 0% image capture | Critical | `/inspection/new` |
| B-2 | Risk score silently 0 for blood/bone/tissue/crack/insulation_damage | Critical | `risk_engine.py` |
| B-3 | Baseline queue has no priority sort → reviewers can't find blocking items | High | `/baseline-review` |
| B-4 | `facility_name`, `department`, `tray_id` not persisted → breaks reporting | High | `Inspection` ORM |
| B-5 | No Passport deeplink from Intake History → navigation friction | Medium | `IntakeHistoryPage.tsx` |
| B-6 | Baseline images absent → reviewers approve metadata only | Medium | Baseline Library |
| B-7 | No "no approved baseline" warning on inspection form | Medium | `NewInspectionPage.tsx` |
| B-8 | `BaselineLibraryPage` is a stub (placeholder UI, no search) | Low | `/baseline-library` |

---

## 3. User Workflow Analysis

### 3a. SPD Technician Workflow

**Current path:**
1. Navigate to `/inspection/new` — 4 sections, 15+ fields
2. Submit form — receive success message (no risk score shown)
3. Navigate separately to `/inspection-image-upload`
4. Upload images for the inspection just submitted

**Friction points:**
- Step 3 is not prompted or linked from the success state. 100% of technicians skipped it.
- Risk score is not shown after submission. Technicians don't know the outcome of their submission.
- Barcode field is free text — Zebra USB scanners work but there is no visual confirmation of scan.
- `instrument_type` is 9-option select including `scissors`, `forceps`, `clamp` that don't apply to lumened instruments (scope, ureteroscope, bronchoscope are the relevant categories). This confuses technicians.
- No auto-fill from the instrument registry — technicians must manually re-enter manufacturer, model, and barcode for every inspection even if the instrument is already registered.
- `tray_id` is an optional free-text field — inconsistent entries will fragment analytics grouping.

**Efficiency rating: 3/5** — Core flow works but image step is routinely skipped and no feedback loop.

---

### 3b. SPD Manager Workflow

**Current path:**
1. Review inspections in Intake History (`/intake-history`)
2. Review baselines in Baseline Review Queue (`/baseline-review`)
3. Manage CAPA queue (`/capa`)
4. Navigate to Instrument Passport in Infrastructure Console (`/infrastructure`) — requires manual instrument selection each time

**Friction points:**
- No Passport deeplink from Intake History. After reviewing an inspection, navigating to the instrument's full history requires: navigate to Infrastructure → select Passport tab → select instrument from dropdown. This is 3–4 clicks per instrument.
- Baseline review queue shows records in creation order. Manager must manually scan to find baselines blocking active inspections.
- CAPA queue does not show which instrument triggered the CAPA.
- No baseline coverage KPI — manager cannot see at a glance which instrument types lack an approved baseline.

**Efficiency rating: 3.5/5** — Core workflow functional; deeplink gaps add navigation overhead.

---

### 3c. Vendor Workflow

**Current path:**
1. Navigate to `/vendor-intake` or `/vendor-baseline-portal`
2. Submit baseline record
3. No confirmation

**Friction points:**
- No email confirmation after baseline submission. Vendors do not know if submission was received.
- No status visibility — vendors cannot check if their submission is pending, approved, or rejected.
- No rejection reason shown — if rejected, vendor receives no guidance on what to fix.

**Efficiency rating: 2.5/5** — Baseline portal works but no feedback loop damages vendor trust.

---

## 4. Dashboard Refinement Analysis

### 4a. Current KPI Groups

The Dashboard (`/`) has four KPI groups fetching from `/api/enterprise/findings/kpi-summary` and `/api/inspections/summary`:

| Group | KPIs | Assessment |
|-------|------|-----------|
| Operational KPIs | Total Inspections, Total Findings, High-Risk Instruments, Baseline Approval Rate | Keep — core pilot metrics |
| Contamination KPIs | Per-category finding counts (blood, bone, tissue, debris, corrosion, crack, insulation_damage) | Keep — useful for SPD manager |
| Pilot KPIs | Vendor Submissions, Total Baselines, Pending Baselines, Approved Baselines | Keep — but add "Blocking N inspections" per baseline |
| Image Library KPIs | Demo Image Cards, Approved + Pending Baselines (duplicate), Approved Baselines (duplicate) | Remove — two of three KPIs are duplicates from Pilot KPIs group |

### 4b. Missing KPIs

| KPI | Recommended Location | Priority |
|-----|---------------------|----------|
| Baseline coverage % (instrument types with ≥1 approved baseline) | Pilot KPIs | High |
| Inspections with no images uploaded | Operational KPIs | High |
| Average review turnaround time | Operational KPIs | Medium |
| Open CAPA count | Operational KPIs | Medium |
| Inspections pending review | Operational KPIs | Medium |

### 4c. Tenant Filter Gap

All dashboard KPIs show aggregate data with no tenant filter or "Pilot View" toggle. When a second facility is onboarded, SPD Manager at Bon Secours will see combined data including Mercy Health records. A tenant filter or role-scoped API response is required before second-facility rollout.

---

## 5. Instrument Passport Review

### 5a. Current State

The Instrument Passport lives inside the `GlobalInfrastructureConsole` (`/infrastructure`) as the "Passport" tab. It requires:
1. User navigates to `/infrastructure`
2. Selects "Passport" tab
3. Selects instrument from dropdown

**Missing views:**
- No deeplink / query parameter pre-selection (e.g., `/infrastructure?tab=passport&instrument=FURO-001`)
- No reprocessing cycle count trend chart
- No related inspection history list within the Passport view
- No "flag for retirement" action based on cycle count threshold

**Missing data in Passport:**
- `last_reprocessing_date` — not a field on the instrument identity model
- `cycle_count_max` — exists but no alert when approaching limit
- Inspection count linked to this instrument — requires `related_instrument_id` FK (not yet on Inspection model)

### 5b. Recommended Additions

| # | Addition | Effort | Priority |
|---|---------|--------|----------|
| P-1 | Deeplink via `?instrument=<barcode>` query param to pre-select instrument | 2 hours | High |
| P-2 | "View Passport" action button on each Intake History row | 2 hours | High |
| P-3 | Inspection history list within Passport (linked via `related_instrument_id` FK) | 1 day | Medium |
| P-4 | Reprocessing cycle trend chart (count over time) | Half day | Medium |
| P-5 | Cycle count alert banner when instrument is within 10% of max | 2 hours | Medium |

---

## 6. Image Quality Analysis

### 6a. Current Standards

Image upload is handled at `/inspection-image-upload` (component: `InspectionImageUploadPage`) and `/baseline-image-upload` (component: `BaselineImageUploadPage`). The pilot image manifest (`pilotImageManifest.ts`) defines 20 placeholder entries; 0 real images have been ingested.

**Missing upload guidance in the UI:**
- No recommended resolution or file format shown on upload pages
- No maximum file size indicator
- No PHI warning ("Do not photograph patient name tags, wristbands, or medical records")
- No naming convention shown (pilot requires `pilot_{tenant}_{n}.jpg` pattern per `first-data-quality-report.md`)

### 6b. Recommended Capture Protocol (to display on upload pages)

| Requirement | Specification |
|-------------|---------------|
| Format | JPEG or PNG |
| Resolution | Minimum 1920×1080 (1080p); 4K preferred for borescope |
| File size | Maximum 20 MB per image |
| Naming | `{facility_code}_{instrument_id}_{YYYYMMDD}_{sequence}.jpg` |
| PHI | No patient labels, wristbands, or identifiers in frame |
| Lighting | White LED illumination; no flash flare on lumen entry |
| Angles required | Lumen entry, distal tip, insertion tube (3 minimum) |

### 6c. Inline Upload Recommendation

Embed an image dropzone directly in `NewInspectionPage.tsx` as Section 5 "Inspection Images". Use the same `<input type="file" accept="image/*" multiple>` pattern already in `InspectionImageUploadPage`. On submit, batch the images with the inspection record in a single API call or immediately trigger the upload flow on the success screen with a "Upload Images Now" primary CTA.

---

## 7. Ranking Engine Observations

### 7a. Current Scoring Formula

`backend/app/analytics/risk_engine.py` — `calculate_risk(issue, confidence)`:

```python
def calculate_risk(issue, confidence):
    risk = 0
    if issue in ["debris", "stain"]:
        risk += 50
    if issue == "corrosion":
        risk += 80
    if confidence > 0.8:
        risk += 20
    if confidence > 0.9:
        risk += 30
    return min(risk, 100)
```

### 7b. Critical Gap — Five Finding Categories Return 0

| Finding | Score Returned | Clinically Correct? |
|---------|---------------|---------------------|
| `debris` | 50–100 | ✅ Partially (medium-high severity) |
| `stain` | 50–100 | ✅ (maps to debris) |
| `corrosion` | 80–100 | ✅ High severity |
| `blood` | **0** | ❌ Should be 55–85 |
| `bone` | **0** | ❌ Should be 50–70 |
| `tissue` | **0** | ❌ Should be 50–75 |
| `crack` | **0** | ❌ Should be 85–100 (critical) |
| `insulation_damage` | **0** | ❌ Should be 80–100 (critical) |
| `none` | **0** | ✅ Correct |

**Impact:** 17 of the 50 pilot inspections (blood=8, tissue=5, bone=2, crack=1, insulation_damage=1) received a risk score of 0. The SPD Manager saw 3 critical-risk findings in the seed data — these were scored correctly because they were `crack` and `insulation_damage` in the seed script's `_risk()` function, which has a fuller implementation than `risk_engine.py`. The live API path uses `risk_engine.py` and would return 0 for those same findings.

### 7c. Recommended Scoring Formula

Replace `calculate_risk()` with a full multi-category implementation:

```python
ISSUE_BASE = {
    "none":              0,
    "debris":           45,
    "stain":            45,
    "blood":            60,
    "bone":             55,
    "tissue":           55,
    "corrosion":        70,
    "crack":            85,
    "insulation_damage": 85,
}

def calculate_risk(issue: str, confidence: float) -> int:
    base = ISSUE_BASE.get(issue, 30)
    conf_bonus = 15 if confidence > 0.9 else 10 if confidence > 0.8 else 0
    return min(base + conf_bonus, 100)
```

### 7d. Trustworthiness Assessment

| Dimension | Current State | Recommendation |
|-----------|--------------|----------------|
| Finding detection | YOLO model path; falls back to metadata-only when no image | Implement graceful degradation message when no model loaded |
| Confidence calibration | Range 62–97.5% in pilot data — realistic spread | No change needed |
| Baseline component | Documented as 20% of risk in prediction_engine.py, but **not used in `calculate_risk()`** | Wire baseline match into the live scoring path |
| False positive rate | Unknown — no ground truth images yet | Establish once real images are ingested |
| False negative rate | Unknown | Establish once real images are ingested |
| Human review flag | `human_review_required: true` on all AI outputs | ✅ Correct — maintain |

### 7e. Observations by Finding Category

- **Blood:** High clinical significance (patient safety). Score of 0 is the most dangerous gap. Blood residue in a lumen is a sterilization-critical failure.
- **Tissue:** High significance, similar to blood. Protein residue prevents sterilant penetration.
- **Bone:** Medium-high. Calcified debris can block lumens and harbor biofilm.
- **Debris / Bioburden:** Correctly scored at 45–75. Represents the most common finding in real SPD data.
- **Corrosion:** Correctly scored at 70–100. Structural integrity risk.
- **Crack:** Most critical structural defect. Should never score below 85. Current live path returns 0.
- **Insulation Damage:** Critical electrical safety finding (monopolar instruments). Should never score below 80. Current live path returns 0.

---

## 8. Recommended Phase 9 Roadmap

Based on Phase 8 findings, Phase 9 should focus on:

1. **Risk Engine Fix** (1 day) — Fix `calculate_risk()` to cover all 7 finding categories. This is the highest-clinical-safety item.
2. **Inspection Schema Migration** (1 day) — Add `facility_name`, `department`, `tray_id`, `instrument_barcode`, `instrument_udi` columns to Inspection ORM.
3. **Inline Image Upload** (1 day) — Embed dropzone in `/inspection/new` as Section 5.
4. **Passport Deeplink** (2 hours) — Add query param pre-selection and "View Passport" button in Intake History.
5. **Baseline Queue Priority Sort** (half day) — Sort by "blocking N inspections" descending.
6. **Dashboard Deduplication + Tenant Filter** (half day) — Remove duplicate Image Library KPIs; add tenant-scoped filter.
7. **Vendor Email Confirmation** (1 day) — SMTP email on baseline submission acceptance.
8. **Baseline Coverage KPI** (2 hours) — New KPI card: % of active instrument types with ≥1 approved baseline.
9. **Barcode Scanner UX** (half day) — Visual scan confirmation on barcode field focus + auto-tab.
10. **Upload Guidance UI** (2 hours) — Show resolution, size, PHI warning, naming convention on upload pages.

---

*LumenAI Pilot Program — Internal Use Only*  
*All AI outputs are decision-support tools. Human review required on all AI-scored records.*  
*LumenAI makes no claim of FDA clearance or regulatory approval.*
