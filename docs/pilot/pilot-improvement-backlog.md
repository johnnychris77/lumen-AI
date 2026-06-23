# Pilot Improvement Backlog — Top 20

**Version:** 1.0  
**Phase:** 8 — Pilot Findings Analysis & UI Refinement  
**Date:** 2026-06-23  
**Source:** `pilot-findings-analysis.md`, `ui-ux-refinement-plan.md`, pilot Week 1 feedback

Priority: **P1** = must-fix before second-facility rollout; **P2** = Sprint 7–8 target; **P3** = Sprint 8–9 nice-to-have

---

## Backlog

| # | Title | Priority | Effort | Impact | Release |
|---|-------|----------|--------|--------|---------|
| 1 | Fix risk scoring for blood, bone, tissue, crack, insulation_damage | P1 | 1 hour | Clinical safety — 34% of findings return score 0 | Sprint 7 |
| 2 | Add facility_name, department, tray_id columns to Inspection ORM | P1 | 1 day | Enables tray and department analytics | Sprint 7 |
| 3 | Embed image upload (or success-screen redirect) in /inspection/new | P1 | 1 day | Fixes 100% image-skip rate from pilot Week 1 | Sprint 7 |
| 4 | Add related_instrument_id FK: Inspection → InstrumentDigitalIdentity | P1 | Half day | Enables Passport deeplink and instrument-level analytics | Sprint 7 |
| 5 | Show risk score and risk level in inspection submission success state | P1 | Half day | Immediate feedback loop for SPD Technician | Sprint 7 |
| 6 | Add "View Passport" deeplink from Intake History rows | P2 | 2 hours | Saves 3–4 clicks per instrument review for SPD Manager | Sprint 7 |
| 7 | Add instrument query param to Infrastructure Console Passport tab | P2 | 2 hours | Enables deeplink pre-selection (`?tab=passport&instrument=FURO-001`) | Sprint 7 |
| 8 | Add uniqueness constraint on (barcode, tenant_id) in instrument registry | P1 | 1 hour | Prevents duplicate instrument registration in live intake | Sprint 7 |
| 9 | Sort baseline review queue by "blocking N inspections" descending | P2 | Half day | Helps SPD Manager prioritize baseline approvals | Sprint 7 |
| 10 | Add "No approved baseline" warning on inspection form | P2 | 2 hours | Prevents deflated risk scores without explanation | Sprint 7 |
| 11 | Add instrument_barcode and instrument_udi columns to Inspection ORM | P2 | Half day | Links inspection to instrument identity without manual lookup | Sprint 7 |
| 12 | Reorder instrument_type select to prioritize lumened scope categories | P2 | 1 hour | Reduces mis-selection for SPD Technician | Sprint 7 |
| 13 | Mobile layout: sm:grid-cols-2 for Instrument Identification section | P2 | 2 hours | Reduces vertical scrolling on mobile devices | Sprint 7 |
| 14 | Scroll-to-first-error on form submit (all forms) | P2 | 2 hours | Prevents missed validation errors on mobile | Sprint 7 |
| 15 | Add baseline coverage KPI card to Dashboard (% instrument types with approved baseline) | P2 | 2 hours | Gives SPD Manager at-a-glance baseline readiness | Sprint 7 |
| 16 | Remove duplicate KPI cards from Dashboard Image Library section | P2 | 1 hour | Reduces confusion from repeated numbers | Sprint 7 |
| 17 | Add barcode scanner visual feedback (scan confirmation + auto-tab) | P2 | 2 hours | Improves Zebra USB scanner usability for SPD Technician | Sprint 7 |
| 18 | Add capture guidelines to image upload pages (resolution, PHI warning, naming) | P2 | 2 hours | Improves image quality for AI scoring | Sprint 7 |
| 19 | Vendor baseline submission confirmation email (SMTP) | P2 | 1 day | Closes vendor feedback loop; reduces re-submission | Sprint 8 |
| 20 | Add finding category tooltips to inspection form | P3 | 2 hours | Answers SPD Educator question; reduces miscategorization | Sprint 8 |

---

## Effort Summary

| Priority | Items | Total Estimated Effort |
|----------|-------|----------------------|
| P1 | 5 items (#1–5 + #8) | 4 days |
| P2 | 13 items (#6–18) | 3.5 days |
| P3 | 2 items (#19–20) | 1 day + 2 hours |

**Total estimated effort: ~8.5 days (Sprint 7–8)**

---

## P1 Detail Specifications

### #1 — Fix Risk Scoring

**File:** `backend/app/analytics/risk_engine.py`

Replace current implementation:

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

Add unit tests covering all 7 categories + boundary confidence values.

---

### #2 — Inspection ORM Migration

**Add to `Inspection` model:**
- `facility_name: str | None`
- `department: str | None`
- `tray_id: str | None`

**Update `/api/inspections` intake route** to write these fields from the POST body (already sent by `NewInspectionPage.tsx`).

**Migration:** `alembic revision --autogenerate -m "add_facility_dept_tray_to_inspection"` then `alembic upgrade head`.

---

### #3 — Inline Image Upload / Success Redirect

**Option A (preferred):** Add Section 5 "Inspection Images" to `NewInspectionPage.tsx` with `<input type="file" accept="image/*" multiple capture="environment">`. On form submit, POST images to `/api/inspection-images/{inspection_id}` immediately after the record is created.

**Option B (quick win):** In the success state of the form, replace "Submit Another" as the primary CTA with "Upload Images for This Inspection →" linking to `/inspection-image-upload?inspection_id={id}`. Add the secondary "Start New Inspection" button.

---

### #4 — related_instrument_id FK

**Add to `Inspection` model:**
- `related_instrument_id: int | None` (FK to `p25_instrument_identities.id`)

**Behavior:** Set during intake if the submitted `barcode` or `udi` matches a registered instrument. Null if no match (new or unregistered instrument).

---

### #5 — Post-Submission Risk Score Display

**In `NewInspectionPage.tsx` success state:**

```tsx
{submittedResult && (
  <div className="flex items-center gap-3 mt-4 p-3 rounded-lg bg-slate-50 border border-slate-200">
    <span className="text-sm text-slate-600">Risk Score:</span>
    <RiskBadge score={submittedResult.risk_score} level={submittedResult.risk_level} />
    <span className="text-xs text-slate-400 ml-auto">Human review required</span>
  </div>
)}
```

API response from `/api/inspections` (POST) must include `risk_score` and `risk_level` — confirm and add if missing.

---

## Acceptance Criteria Checklist

### Sprint 7 Gate (before second-facility onboarding)

- [ ] `calculate_risk()` returns non-zero for blood, bone, tissue, crack, insulation_damage
- [ ] `facility_name`, `department`, `tray_id` columns exist on inspections table and are populated
- [ ] Inspection form shows image upload prompt or redirect after submission
- [ ] Risk score visible in success state after form submission
- [ ] `(barcode, tenant_id)` unique constraint active in instrument registry
- [ ] "No approved baseline" warning shown when instrument_type has no approved baseline
- [ ] "View Passport" link present on Intake History rows
- [ ] Baseline review queue sorted by blocking count by default

### Sprint 8 Gate (before GA rollout)

- [ ] All P2 items from backlog completed
- [ ] Vendor baseline confirmation email working
- [ ] BaselineLibraryPage renders searchable approved baseline list
- [ ] Dashboard has tenant filter or role-scoped data
- [ ] Image upload guidance shown on upload pages
- [ ] Real inspection images ingested for ≥5 instruments at Bon Secours

---

## Out of Scope (Phase 8)

The following were requested but are deferred to Phase 9 or later:

- Auto-fill instrument details from registry on barcode scan (requires instrument lookup API integration)
- k-anonymity network-contributed baseline publication (requires ≥5 contributing tenants)
- SSO / SAML authentication (deferred from Phase 7)
- EHR integration (out of scope for pilot)
- Daily summary email for SPD Manager
- Instrument risk heat map (instrument × finding matrix)
- Barcode scanner hardware-level integration (USB HID confirmed working; deep integration deferred)

---

*LumenAI Pilot Program — Internal Use Only*  
*Backlog items are recommendations, not commitments. Prioritization subject to engineering capacity and clinical review.*  
*LumenAI makes no claim of FDA clearance or regulatory approval. All AI outputs require qualified human review.*
