# LumenAI Inspection Intelligence — Pilot Guide

**Version:** 1.0  
**Milestone:** P2D — Pilot Readiness  
**Audience:** SPD Managers, Hospital Administrators, Vendor Users, Executives, Evaluators

---

## 1. Pilot Narrative

LumenAI Inspection Intelligence provides AI-assisted sterile processing governance for surgical instrument inspection. During the pilot, evaluators can walk through the complete lifecycle:

1. A **vendor** submits a manufacturer baseline for an instrument (catalog number, IFU, acceptable-condition image metadata, barcode/QR/KeyDot identifiers).
2. A **hospital administrator** reviews and approves the baseline.
3. An **SPD operator** submits an inspection finding (AI-detected bioburden, blood, bone, tissue, debris, corrosion, crack, or insulation damage).
4. The system compares the finding against the approved baseline and generates a **baseline-aware confidence score**.
5. The score, baseline comparison, and audit trail are packaged into a tamper-evident **governance packet** available for export.

---

## 2. User Roles

| Role | Header Value | Typical Actions |
|---|---|---|
| `viewer` | `X-LumenAI-Role: viewer` | View dashboard, read queues |
| `operator` | `X-LumenAI-Role: operator` | Submit inspection intakes, view governance packets |
| `vendor` | `X-LumenAI-Role: vendor` | Submit vendor baselines via the portal |
| `hospital_admin` | `X-LumenAI-Role: hospital_admin` | Approve or reject vendor baselines, trigger CAPA |
| `enterprise_admin` | `X-LumenAI-Role: enterprise_admin` | Full access including executive dashboard |

---

## 3. Demo Workflow (Step-by-Step)

### Step 1 — View the Dashboard
- URL: `/`
- Shows: total inspections, enterprise finding KPIs (by category), baseline lifecycle KPIs, recent inspection activity, module health
- Key KPI cards: Blood, Bone, Tissue, Debris, Corrosion, Crack, Insulation Damage, Baseline Match, Barcode/QR/KeyDot

### Step 2 — Submit a Vendor Baseline
- URL: `/vendor-baseline-portal`
- Role: `vendor`
- Action: Submit a new baseline for an instrument model (e.g., "Stryker Frazier Suction 8Fr")
- Fields: vendor name, instrument name, catalog number, barcode/QR/KeyDot values, IFU reference, acceptable condition notes

### Step 3 — Review and Approve the Baseline
- URL: `/baseline-review`
- Role: `hospital_admin`
- Action: Approve the submitted baseline. Rejected baselines are logged with reason.
- Result: Baseline status changes to `approved`, activating it for scoring.

### Step 4 — Submit an Inspection Intake
- URL: `/vendor-intake`
- Role: `operator`
- Form fields: facility, department, vendor, instrument, finding category, severity, confidence score, recommended action
- Supports all finding types: bioburden/debris, blood, bone, tissue, corrosion, crack, insulation damage
- On submit: returns finding_id, risk_score_id, disposition_id, evidence_id

### Step 5 — View Manufacturer Baselines
- URL: `/manufacturer-baselines`
- Role: `viewer` or `operator`
- Shows: all baselines on file, approval status, IFU references, baseline comparison triggers

### Step 6 — Review Intake History
- URL: `/intake-history`
- Role: `operator`, `hospital_admin`, `enterprise_admin`
- Shows: complete audit-ready record of all intakes with export options (CSV, XLSX, JSON, ZIP bundle)

---

## 4. Sample Pilot Data

The following fixtures are seeded by `backend/app/seed_demo.py`:

### Facility
- Name: St. Mary's Hospital
- Type: Hospital
- Region: Mid-Atlantic
- Tenant: `demo-tenant`

### Vendor
- Name: Stryker Medical Devices
- Type: Medical Device
- Risk Tier: Tier 1

### Instrument
- Name: Frazier Suction Tube 8Fr
- Type: Lumened Instrument
- IFU: IFU-STRYKER-FRAZ-8FR-v2.1
- Model: FRAZ-8FR-001

### Vendor Baselines
| Status | Instrument | Catalog |
|---|---|---|
| `pending_hospital_review` | Frazier Suction Tube 8Fr | FRAZ-8FR-001 |
| `approved` | Kerrison Rongeur 3mm | KR-3MM-STR |

### Pilot Findings (one per category)
| Category | Severity | Description |
|---|---|---|
| blood / retained blood residue | critical | Blood residue in lumen channel |
| bone / bone fragment | high | Bone fragment at distal port |
| tissue / retained tissue | high | Retained soft tissue at instrument tip |
| debris / retained debris | medium | Non-biological debris in lumen |
| corrosion / surface rust | medium | Surface corrosion on shaft |
| crack / hairline fracture | critical | Hairline crack near instrument hub |
| insulation damage | critical | Insulation degradation on electrosurgical instrument |

### Identifiers (for barcode/QR/KeyDot matching)
- Barcode: `STRYKER-FRAZ-8FR-001`
- QR Code: `QR-STR-FRAZ-8FR-001`
- Key Dot: (not set for this instrument)
- UDI: `IFU-STRYKER-FRAZ-8FR-v2.1`

---

## 5. Routes & Pages

| Route | Component | Purpose |
|---|---|---|
| `/` | `Dashboard` | Live KPI overview |
| `/vendor-intake` | `VendorIntake` | Submit new inspection finding |
| `/manufacturer-baselines` | `ManufacturerBaselinePanel` | View instrument baselines |
| `/baseline-review` | `BaselineReviewQueue` | Hospital admin baseline approval |
| `/vendor-baseline-portal` | `VendorBaselineSubscriptionPortal` | Vendor baseline submission |
| `/intake-history` | `EnterpriseIntakeHistoryPanel` | Full audit-ready history |
| `/findings` | `FindingsQueuePage` | Enterprise findings queue |
| `/capa` | `CapaQueuePage` | CAPA workflow |
| `/analytics` | `AnalyticsDashboardPage` | Analytics views |

---

## 6. API Dependencies

| Endpoint | Purpose |
|---|---|
| `GET /api/enterprise/findings/kpi-summary` | Dashboard KPI cards (all categories + baselines) |
| `POST /api/enterprise/intake` | Submit inspection finding |
| `GET /api/enterprise/vendor-baseline-subscription/baselines` | List vendor baselines |
| `POST /api/enterprise/vendor-baseline-subscription/baselines` | Submit vendor baseline |
| `POST /api/enterprise/vendor-baseline-subscription/baselines/{id}/approve` | Approve baseline |
| `GET /api/enterprise/vendor-baseline-subscription/baselines/{id}/audit` | Baseline audit trail |
| `POST /api/enterprise/intake/{id}/baseline-comparison` | Compare finding to baseline |
| `POST /api/enterprise/baseline-aware-score` | 4-tier confidence scoring |
| `GET /api/enterprise/baseline-review-queue` | Baselines pending review |
| `GET /api/history/summary` | Inspection workflow summary |
| `GET /api/history` | Recent inspection records |

---

## 7. Success Criteria

The pilot is considered successful when an evaluator can:

- [ ] View the dashboard with live KPI data for all 10 finding categories
- [ ] Submit a vendor baseline from the portal and see it appear in the review queue
- [ ] Approve the baseline as a hospital administrator
- [ ] Submit a new inspection intake with all required fields validated
- [ ] View the resulting finding in intake history
- [ ] Confirm the baseline-aware confidence score is returned with correct tier
- [ ] Export the intake history as CSV or XLSX
- [ ] Navigate between all 6 pilot pages without errors or blank screens

---

## 8. Known Limitations

| Area | Status | Notes |
|---|---|---|
| Authentication (dev vs. production) | ✅ Resolved | `AUTH_MODE=dev` for pilot. Set `AUTH_MODE=oidc` + `OIDC_ISSUER_URL` + `OIDC_AUDIENCE` for production JWKS. See `backend/.env.example`. |
| Baseline image upload | ✅ Resolved | File upload UI added. `POST /api/enterprise/vendor-baseline-subscription/baselines/upload-image` stores locally (dev) or to S3 (production). See `LUMENAI_STORAGE_BACKEND` in `.env.example`. |
| Barcode/QR/KeyDot scan | ✅ Resolved | Camera scanner built into Vendor Intake form using native `BarcodeDetector` API. Requires Chrome 83+ or Edge 83+. Falls back to typed input in other browsers. |
| Dashboard auto-refresh | ✅ Resolved | Dashboard polls every 30 seconds with a visible countdown and manual Refresh button. |
| Multi-tenant isolation | Active (by design) | Demo uses `demo-tenant`. All users see all records in `AUTH_MODE=dev`. Tenant isolation enforces per-tenant scope in `AUTH_MODE=oidc` via JWT claims. |
| PDF generation | Active | Governance packet PDF requires `reportlab`. Falls back to JSON if not installed. Fix: `pip install reportlab`. |

---

## 9. Running the Demo Seed

```bash
cd backend
DATABASE_URL=sqlite:///./lumenai.db PYTHONPATH=. python -m app.seed_demo
```

Idempotent — safe to run multiple times. Creates all pilot fixtures if not already present.

---

## 10. Validation Commands

```bash
# Frontend build
npm --prefix frontend run build

# Backend lint
ruff check backend/app backend/tests

# Backend tests
cd backend && PYTHONPATH=. python -m pytest tests -q
```
