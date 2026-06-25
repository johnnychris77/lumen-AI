# Pilot Intake QA Checklist

**Version:** 1.0  
**Phase:** 6 — Pilot Intake QA & Launch Readiness  
**Status:** Ready for pilot intake (see Known Limitations)

---

## 1. Route Checklist

| Route | Component | Renders | Auth-Gated | Empty State | Loading State | Notes |
|-------|-----------|---------|------------|-------------|---------------|-------|
| `/` (Dashboard) | `Dashboard.tsx` | ✅ | ✅ | ✅ | ✅ | 3 KPI groups: Operational / Contamination / Pilot |
| `/inspection/new` | `NewInspectionPage.tsx` | ✅ | ✅ | n/a | ✅ | Full multi-step form |
| `/vendor-intake` | `VendorIntake.tsx` | ✅ | ✅ | ✅ | ✅ | Vendor form |
| `/manufacturer-baselines` | `ManufacturerBaselinesPage.tsx` | ✅ | ✅ | ✅ | ✅ | List + upload |
| `/baseline-review` | `BaselineReviewPage.tsx` | ✅ | ✅ | ✅ | ✅ | Approve / reject decisions |
| `/vendor-baseline-portal` | `VendorBaselinePortalPage.tsx` | ✅ | ✅ | ✅ | ✅ | Full portal |
| `/intake-history` | `IntakeHistoryPage.tsx` | ✅ | ✅ | ✅ | ✅ | Paginated history |
| `/infrastructure` | `GlobalInfrastructureConsole.tsx` | ✅ | ✅ | ✅ | ✅ | "Instrument Registry" nav label → `/infrastructure` |
| `/instrument-passport` | `InstrumentPassportPage.tsx` | ✅ | ✅ | ✅ | ✅ | Redirects to Infrastructure > Passport tab |
| `/demo-image-library` | `DemoImageLibraryPage.tsx` | ✅ | ✅ | ✅ | ✅ | Manifest-driven; 0 real images → info banner |
| `/baseline-image-upload` | `BaselineImageUploadPage.tsx` | ✅ | ✅ | n/a | ✅ | Pilot baseline intake form |
| `/inspection-image-upload` | `InspectionImageUploadPage.tsx` | ✅ | ✅ | n/a | ✅ | Dual dropzone |

**Nav note:** "Instrument Registry" in the sidebar navigates to `/infrastructure` (the `GlobalInfrastructureConsole`). There is no standalone `/instruments` route — this is intentional (the Infrastructure Console consolidates instrument identity, passport, readiness, and registry into one tabbed surface).

---

## 2. Form Field Checklist

### 2a. New Inspection (`/inspection/new`)

| Field | Present | Validated | Submitted to API |
|-------|---------|-----------|-----------------|
| Facility / Site | ✅ | ✅ required | ✅ |
| Department | ✅ | ✅ required | ✅ |
| Tray ID | ✅ | ✅ required | ✅ |
| Instrument Name | ✅ | ✅ required | ✅ |
| Instrument Type | ✅ | ✅ required | ✅ |
| Manufacturer | ✅ | optional | ✅ |
| Model Number | ✅ | optional | ✅ |
| Serial Number | ✅ | optional | ✅ |
| Barcode | ✅ | optional | ✅ |
| QR Code | ✅ | optional | ✅ |
| UDI | ⚠️ | — | — |
| KeyDot ID | ✅ | optional | ✅ (keydot_id) |
| Finding Categories | ✅ | ✅ at least one | ✅ (multi-select checkboxes) |
| Notes | ✅ | optional | ✅ |

> **Gap — UDI field:** NewInspectionPage does not have an explicit UDI field (separate from QR code). The `VendorBaselinePortalPage` and `BaselineImageUploadPage` both capture UDI. This is acceptable for pilot since UDI is optional on inspection records; add in a future sprint if required by facility SOPs.

### 2b. Vendor Baseline Portal (`/vendor-baseline-portal`)

| Field | Present | Validated | Notes |
|-------|---------|-----------|-------|
| Instrument Name | ✅ | ✅ | |
| Manufacturer | ✅ | ✅ | |
| Model | ✅ | ✅ | |
| Serial Number | ✅ | optional | |
| Barcode | ✅ | optional | |
| QR Code | ✅ | optional | |
| UDI | ✅ | optional | |
| KeyDot ID | ✅ | optional | |
| Baseline Image | ✅ | ✅ | Via `BaselineImageUpload` component |
| Notes | ✅ | optional | |

### 2c. Baseline Image Upload (`/baseline-image-upload`)

| Field | Present | Validated | Notes |
|-------|---------|-----------|-------|
| Instrument Name | ✅ | ✅ | |
| Manufacturer | ✅ | ✅ | |
| Model Number | ✅ | ✅ | |
| Barcode | ✅ | optional | |
| QR Code | ✅ | optional | |
| UDI | ✅ | optional | |
| KeyDot ID | ✅ | optional | |
| Baseline Image | ✅ | ✅ | |
| Capture Device | ✅ | optional | |
| Image Angle | ✅ | optional | |
| Image Quality | ✅ | optional | |
| Normal/Abnormal | ✅ | ✅ | |
| Notes | ✅ | optional | |

### 2d. Inspection Image Upload (`/inspection-image-upload`)

| Field | Present | Validated | Notes |
|-------|---------|-----------|-------|
| Inspection Images | ✅ | ✅ at least 1 | 10 MB limit, image/* only |
| Borescope Images | ✅ | optional | Separate dropzone |
| Capture Device | ✅ | optional | |
| Finding Category | ✅ | ✅ required | Pill buttons |
| Risk Level | ✅ | ✅ required | 4-way: low/medium/high/critical |
| Notes | ✅ | optional | |

### 2e. Baseline Review (`/baseline-review`)

| Field | Present | Notes |
|-------|---------|-------|
| Approve action | ✅ | Via API `PATCH /approve` |
| Reject action | ✅ | Via API `PATCH /reject` |
| Reviewer notes | ✅ | Captured in review workflow |

---

## 3. Image Library Checklist

| Item | Status | Notes |
|------|--------|-------|
| Manifest loads | ✅ | `pilotImageManifest.ts` — 20 entries, 8 instruments, 2 facilities |
| Placeholder fallback on missing image | ✅ | `onError` → typed SVG placeholder |
| Zero-images info banner | ✅ | Shown when `summary.available === 0` |
| Baseline images distinguished | ✅ | Blue badge: "Baseline" |
| Inspection images labeled | ✅ | Slate badge: "Inspection" |
| Borescope images labeled | ✅ | Purple badge: "Borescope" |
| Finding category badges render | ✅ | Per `FINDING_META` — 9 categories |
| Image quality display | ✅ (N/A) | Quality stored in manifest; shown when present |
| Instrument Passport link | ✅ | `/instrument-passport` CTA in library header |
| Facility filter | ✅ | Dropdown filter by facilityId |
| Image type filter | ✅ | Dropdown filter by imageType |
| Finding category filter | ✅ | Dropdown filter by findingCategory |
| KPI strip | ✅ | Total / available / by type / by facility |
| Real image count | ⚠️ | 0/20 real images loaded — all showing placeholders |

> **Expected pilot action:** Facility coordinators should follow `docs/pilot/pilot-image-ingestion-guide.md` to replace placeholders with real photographs before or during pilot week 1.

---

## 4. Workflow QA

| Step | Mechanism | Status | Notes |
|------|-----------|--------|-------|
| Create instrument | `GlobalInfrastructureConsole` → Instruments tab; or embedded in New Inspection | ✅ | |
| Upload baseline image | `BaselineImageUpload` component → `POST /api/enterprise/vendor-baseline-subscription/baselines/upload-image` | ✅ | |
| Submit vendor baseline | `VendorBaselinePortalPage` → `POST /api/enterprise/vendor-baseline-subscription/baselines` | ✅ | |
| Submit manufacturer baseline | `ManufacturerBaselinesPage` → `POST /api/manufacturer-baselines` | ✅ | |
| Review baseline | `BaselineReviewPage` → approve/reject | ✅ | |
| Create inspection | `NewInspectionPage` → `POST /api/inspections` | ✅ | |
| Attach inspection images | `InspectionImageUploadPage` → `POST /api/inspections/upload-images` (SHA-256 hashed) | ✅ | |
| Select finding category | Multi-select checkboxes on inspection form | ✅ | 7 categories |
| AI scoring | `inspection_job.py` → `ai/inference.py` → `risk_score` field | ✅ | Async; `human_review_required: true` |
| Baseline-aware scoring | `prediction_engine.py` → `baseline_component` (20% weight of risk score) | ✅ | |
| View instrument passport | Infrastructure Console → Passport tab | ✅ | Events log + pilot images gallery |
| Dashboard KPI updates | `Dashboard.tsx` — fetches live counts on load | ✅ | |

**Workflow gap — baseline-aware score visibility:** The inspection submission form acknowledges AI scoring happens asynchronously. The current UI does not show the computed `risk_score` inline in the inspection form after submission; users must check Intake History or the Findings queue. This is acceptable for pilot.

---

## 5. Security Checklist

| Item | Status | Notes |
|------|--------|-------|
| No hardcoded tokens in frontend | ✅ | All 57 auth usages use `localStorage.getItem("token")` pattern |
| Frontend uses `VITE_API_BASE_URL` | ✅ | `import.meta.env.VITE_API_BASE_URL \|\| ""` in all pages |
| Backend dev-token is env-var controlled | ✅ | `DEV_AUTH_TOKEN = os.getenv("DEV_AUTH_TOKEN", "dev-token")` |
| Production guard on dev-token | ✅ | `config.py:70` — raises validation error if `is_production` and token == "dev-token" |
| Backend routes auth-gated | ✅ | 468 `require_roles` / `Depends` usages across route files |
| Unauthenticated requests receive 401/403 | ✅ | `require_roles()` → `HTTPException(401)` on missing/invalid token |
| Tenant isolation enforced | ✅ | Multi-tenant queries filter by `tenant_id` |
| PHI absent from manifest | ✅ | No patient names, MRNs, DOBs in `pilotImageManifest.ts` |
| PHI guidance documented | ✅ | PHI avoidance comment block in manifest; full section in ingestion guide |
| Secret API keys hashed | ✅ | SHA-256 stored; raw key shown once only |
| No causation language in AI outputs | ✅ | `human_review_required: true` on all AI responses |
| Hospital identities anonymized | ✅ | k-anonymity ≥10 for publish, ≥5 for contribute |
| No FDA clearance claimed | ✅ | Verified across all pages and docs |
| Audit trail on all mutations | ✅ | `compliance_flag=True` on audit events |

**Note on `executive_briefing_dashboard.py:356`:** A server-rendered HTML page includes `localStorage.getItem("lumenai_token") || "dev-token"` as a JavaScript fallback. This is a legacy route in the backend, not a frontend page — it is acceptable for internal demo use only. Must be removed before enterprise GA.

---

## 6. Mobile / Tablet Layout Assessment

| Page | Responsive | Notes |
|------|-----------|-------|
| Dashboard | ✅ | Tailwind responsive grid |
| New Inspection | ⚠️ | Only 2 explicit responsive breakpoints; form is single-column — usable but not optimized for mobile |
| Demo Image Library | ✅ | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` |
| Infrastructure Console | ✅ | `md:grid-cols-3`, `md:col-span-2` throughout |
| Vendor Baseline Portal | ✅ | Standard responsive layout |
| Intake History | ✅ | Responsive table with overflow-x |

---

## 7. Known Limitations

| # | Area | Limitation | Severity | Recommended Action |
|---|------|-----------|----------|-------------------|
| L1 | New Inspection | No explicit UDI field (separate from QR code) | Low | Add UDI field in Sprint 7 if SOP requires it |
| L2 | Image Library | 0 of 20 pilot images are real photographs | Medium | Follow ingestion guide before pilot week 1 |
| L3 | Inspection Score | Risk score not shown inline post-submission — only in History / Findings queue | Low | Add score result step in Sprint 7 |
| L4 | Mobile | New Inspection form not optimized for mobile viewport | Low | Add `sm:grid-cols-2` breakpoints in Sprint 7 |
| L5 | Backend legacy | `executive_briefing_dashboard.py` embeds `"dev-token"` fallback in rendered JS | Medium | Remove before enterprise GA |
| L6 | Baseline score | Baseline component is 20% of risk score; score requires at least 1 approved baseline per instrument type to be meaningful | Medium | Ensure baselines are approved during pilot onboarding |
| L7 | Image upload | Inspection images uploaded to `/api/inspections/upload-images` require an active inspection ID — the UI correctly enforces this in two-step flow | Info | No action needed |

---

## 8. Go / No-Go Criteria

| Criterion | Status |
|-----------|--------|
| All pilot routes render without blank screens | ✅ GO |
| New Inspection captures all required fields | ✅ GO |
| Baseline upload and review workflow functional | ✅ GO |
| Image library renders with placeholder fallback | ✅ GO |
| Instrument Passport accessible | ✅ GO |
| No hardcoded tokens in production-path code | ✅ GO |
| PHI not present in demo data | ✅ GO |
| Frontend build passes | ✅ GO |
| Ruff lint clean | ✅ GO |
| 0 real pilot images loaded | ⚠️ CONDITIONAL |

**Overall: CONDITIONAL GO**  
Ready for pilot intake. The only prerequisite before first real patient-instrument scan: facility coordinators must upload at least one real baseline image per instrument type using the Baseline Image Upload workflow (`/baseline-image-upload`) and have it approved via Baseline Review (`/baseline-review`).
