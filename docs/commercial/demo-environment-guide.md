# LumenAI Demo Environment Guide

> **Audience:** Sales engineers and account executives running LumenAI demos and proofs-of-value.

---

## 1. Purpose

Provide a repeatable, safe demo environment that showcases LumenAI's value without using real patient or customer data, and without making clinical or regulatory claims.

---

## 2. Demo Environment Principles

- **No PHI, ever.** Demos use synthetic/seeded data only.
- **Dev auth only in non-production.** The demo backend runs with `ENABLE_DEV_AUTH=true` and a demo token; production never enables dev auth.
- **Isolated tenant.** Each demo uses a dedicated `tenant_id` so no demo data mixes with real accounts.
- **Honest framing.** All AI outputs are presented as candidate signals requiring human review. Never claim FDA clearance or guaranteed clinical outcomes.

---

## 3. Environment Setup

### Backend
```bash
cd backend
DATABASE_URL=sqlite:///./lumenai_demo.db \
ENABLE_DEV_AUTH=true \
DEV_AUTH_TOKEN=demo-token \
AUTH_MODE=dev \
APP_ENV=development \
uvicorn app.main:app --reload
```

### Frontend
```bash
VITE_API_BASE_URL=http://localhost:8000 npm --prefix frontend run dev
```

Authentication in the demo uses the standard localStorage token pattern:
```
Authorization: Bearer <token from localStorage>
```

> Never hardcode tokens in the frontend. The demo token is set in localStorage at login, exactly like production.

---

## 4. Demo Data Seeding

Seed a demo tenant with representative inspections, baselines, and an enterprise hierarchy so dashboards render meaningfully:

1. Create a health system + facilities via `POST /api/enterprise/...`
2. Submit a spread of inspections (mix of clean and contamination-detected)
3. Upload and approve a few baselines
4. Advance an onboarding workflow partway to show progress states

Target volume: ~150–250 inspections in the demo tenant so utilization and health scores land in the "healthy" band.

---

## 5. Demo Workflows

### 5.1 SPD Technician Flow (5 min)
1. New inspection → upload image → AI finding with confidence
2. Show "human review required" framing and disposition step
3. Inspection appears in history with audit trail

### 5.2 Quality Manager Flow (5 min)
1. Quality dashboard → contamination trend
2. Alert review → CAPA linkage
3. Baseline review & approval

### 5.3 Executive Flow (7 min)
1. Enterprise executive scorecard (`/api/enterprise/dashboards/executive-scorecard`)
2. System quality dashboard with outlier facilities
3. Facility readiness scores
4. **ROI calculator** (`POST /api/commercial/roi/calculate`) — show modeled labor + quality savings, payback months
5. **Executive business case** (`GET /api/commercial/business-case/executive-summary`)

### 5.4 Pricing & Packaging Flow (3 min)
1. `GET /api/commercial/packages` — walk the four tiers
2. `POST /api/commercial/pricing/estimate` — live estimate for the prospect's facility count and term
3. Frame land-and-expand path

---

## 6. ROI Calculator in Demos

The ROI calculator uses the same validated pilot constants as production analytics:

| Constant | Value |
|----------|-------|
| Minutes saved per inspection | 4.5 |
| Staff cost per hour | $35 |
| Reprocessing cost avoided | $85 (60% capture) |
| Surgical cancellation cost avoided | $12,000 (1% capture) |

Always present ROI as a **model**, not a guarantee, and offer to validate assumptions with the prospect's own numbers.

---

## 7. Demo Do's and Don'ts

**Do:**
- Use synthetic data
- Emphasize human-in-the-loop review
- Show the audit trail
- Tailor the facility count in the pricing estimate to the prospect

**Don't:**
- Use real patient images or customer data
- Claim FDA clearance or regulatory approval
- Claim causation between LumenAI and clinical outcomes
- Promise specific ROI as a guarantee

---

## 8. Post-Demo

- Send the modeled ROI summary and pricing estimate
- Offer a structured pilot (see `docs/pilot/`) for proof-of-value
- Log the opportunity and recommended tier in CRM

---

*LumenAI does not claim FDA clearance or regulatory approval. All AI outputs in demos are candidate signals requiring human review.*
