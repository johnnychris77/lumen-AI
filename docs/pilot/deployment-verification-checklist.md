# LumenAI Deployment Verification Checklist

**Version:** 1.0  
**Phase:** 7 — Pilot Site Deployment  
**Facility:** Bon Secours Pilot Site  
**Environment:** Pilot (non-production)

---

## Pre-Deployment Requirements

| # | Requirement | Owner | Status |
|---|-------------|-------|--------|
| 1 | `DATABASE_URL` set to pilot PostgreSQL instance | DevOps | ☐ |
| 2 | `DEV_AUTH_TOKEN` set to facility-specific secret (not "dev-token") | DevOps | ☐ |
| 3 | `DEV_SPD_MANAGER_TOKEN` set | DevOps | ☐ |
| 4 | `ENABLE_DEV_AUTH=true` set | DevOps | ☐ |
| 5 | `VITE_API_BASE_URL` set to backend URL in `.env.production` | DevOps | ☐ |
| 6 | `SECRET_KEY` set (32+ char random string) | DevOps | ☐ |
| 7 | S3 bucket (or local storage path) configured | DevOps | ☐ |
| 8 | CORS origin whitelist includes frontend domain | DevOps | ☐ |
| 9 | SSL/TLS certificate active | DevOps | ☐ |
| 10 | Pilot data seed run: `python scripts/seed_pilot_data.py` | DBA | ☐ |

---

## 1. Backend Reachability

```bash
curl -s https://<BACKEND_URL>/health | jq .
# Expected: {"status": "ok", ...}
```

| Check | Expected | Result |
|-------|----------|--------|
| `GET /health` returns 200 | `{"status": "ok"}` | ☐ |
| Response time < 500 ms | < 500 ms | ☐ |
| No SSL warnings | Clean cert | ☐ |

---

## 2. Frontend Reachability

| Check | Method | Result |
|-------|--------|--------|
| Frontend URL loads in browser | Navigate to `https://<FRONTEND_URL>` | ☐ |
| Login page renders | `/login` visible, no blank screen | ☐ |
| No JS console errors on load | Browser devtools → Console | ☐ |
| Assets load (fonts, icons, CSS) | Network tab — no 404s | ☐ |

---

## 3. Authentication

```bash
# Test login endpoint
curl -s -X POST https://<BACKEND_URL>/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "spd_manager", "password": "..."}' | jq .
```

| Check | Expected | Result |
|-------|----------|--------|
| Login returns token | `{"access_token": "..."}` | ☐ |
| Token stored in localStorage | `localStorage.getItem("token")` → non-null | ☐ |
| Unauthenticated request → 401 | `curl /api/inspections` without header → 401 | ☐ |
| Wrong token → 401 | `Authorization: Bearer bad-token` → 401 | ☐ |
| Role header enforced | Viewer cannot POST inspection → 403 | ☐ |

---

## 4. Dashboard

| Check | Method | Result |
|-------|--------|--------|
| `/` loads with KPI cards | Navigate while logged in | ☐ |
| Operational KPIs render (not 0/null) | After seed: inspections ≥ 50 | ☐ |
| Contamination KPIs render | After seed: blood ≥ 8 | ☐ |
| Pilot KPIs render | After seed: baselines ≥ 25 | ☐ |
| No loading spinner stuck | < 3 s to load | ☐ |
| No console errors | Browser devtools | ☐ |

---

## 5. Navigation

| Route | Expected | Result |
|-------|----------|--------|
| `/inspection/new` | New Inspection form renders | ☐ |
| `/intake-history` | Inspection history table renders | ☐ |
| `/vendor-intake` | Vendor intake form renders | ☐ |
| `/manufacturer-baselines` | Baselines list renders | ☐ |
| `/baseline-review` | Review queue renders | ☐ |
| `/vendor-baseline-portal` | Portal renders | ☐ |
| `/infrastructure` | Infrastructure Console renders | ☐ |
| `/instrument-passport` | Passport tab accessible | ☐ |
| `/demo-image-library` | Image library renders | ☐ |
| `/baseline-image-upload` | Upload form renders | ☐ |
| `/inspection-image-upload` | Dual dropzone renders | ☐ |

---

## 6. Upload Functionality

| Check | Method | Result |
|-------|--------|--------|
| Inspection image upload (JPEG < 10 MB) | `/inspection-image-upload` → drag-drop → submit | ☐ |
| Borescope image upload | Second dropzone | ☐ |
| Baseline image upload | `/baseline-image-upload` → upload component | ☐ |
| File > 10 MB rejected | Drag 11 MB file → validation error | ☐ |
| Non-image file rejected | Drag `.pdf` → validation error | ☐ |
| Upload returns image URL | Response includes `baseline_image_url` | ☐ |

---

## 7. Image Rendering

| Check | Method | Result |
|-------|--------|--------|
| Demo Image Library loads | `/demo-image-library` | ☐ |
| Placeholder SVGs render for all 4 types | Before real images are loaded | ☐ |
| `onError` fallback fires on broken src | Temporarily rename one placeholder | ☐ |
| Instrument Passport image gallery shows | Infrastructure → Passport tab → select instrument | ☐ |
| Image type badges render (blue/slate/purple/red) | Demo Image Library | ☐ |

---

## 8. API Smoke Tests

```bash
TOKEN="Bearer <your-token>"

# List inspections
curl -s https://<BACKEND_URL>/api/inspections \
  -H "Authorization: $TOKEN" | jq '.total'

# List baselines
curl -s https://<BACKEND_URL>/api/network/baselines \
  -H "Authorization: $TOKEN" | jq '.total'

# List instruments
curl -s https://<BACKEND_URL>/api/infrastructure/instruments \
  -H "Authorization: $TOKEN" | jq 'length'
```

| Endpoint | Expected After Seed | Result |
|----------|--------------------|----|
| `GET /api/inspections` | 200, items ≥ 50 | ☐ |
| `GET /api/network/baselines` | 200, items ≥ 25 | ☐ |
| `GET /api/infrastructure/instruments` | 200, items ≥ 10 | ☐ |
| `GET /api/infrastructure/dashboard` | 200, summary object | ☐ |

---

## 9. Deployment Verdict

| Area | Status |
|------|--------|
| Backend reachable | ☐ GO / ☐ NO-GO |
| Frontend reachable | ☐ GO / ☐ NO-GO |
| Authentication working | ☐ GO / ☐ NO-GO |
| Dashboard loads with data | ☐ GO / ☐ NO-GO |
| Navigation complete | ☐ GO / ☐ NO-GO |
| Uploads functional | ☐ GO / ☐ NO-GO |
| Images rendering | ☐ GO / ☐ NO-GO |

**Overall:**  ☐ GO — proceed to data collection  
**Overall:**  ☐ NO-GO — resolve blockers before user onboarding

---

*LumenAI Pilot Program — Internal Use Only*  
*This checklist must be completed and signed by the Deployment Lead before user onboarding begins.*
