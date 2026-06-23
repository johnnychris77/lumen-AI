# Production Deployment Guide

**Version:** Phase 11  
**Date:** 2026-06-23  
**Audience:** LumenAI Engineering, DevOps, Customer IT  
**Purpose:** Step-by-step production deployment from infrastructure provisioning to first live inspection

---

## Architecture Overview

```
Frontend (React/Vite)     Backend (FastAPI)      Database
─────────────────────     ─────────────────      ──────────
Render / Vercel  ───────► Render / Railway  ───► PostgreSQL
                                  │
                          Image Storage (S3 / GCS)
```

- **Frontend:** Static SPA, served via CDN. No server-side rendering.
- **Backend:** FastAPI + SQLAlchemy. Stateless — all state in PostgreSQL.
- **Database:** PostgreSQL 15+ in production (SQLite for dev/test only).
- **Image Storage:** Object storage for baseline and inspection images.
- **Auth:** JWT tokens, SHA-256 hashed API keys. No hardcoded credentials.
- **Multi-tenancy:** All queries scoped by `tenant_id`. Tenants cannot see each other's data.

---

## Step 1 — Environment Variables

Set the following in your deployment environment (never commit to source control):

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/lumenai

# Auth
SECRET_KEY=<64-char random string via secrets.token_urlsafe(48)>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# SMTP (for approval notifications)
SMTP_HOST=smtp.yourprovider.com
SMTP_PORT=587
SMTP_USER=noreply@yourdomain.com
SMTP_PASSWORD=<smtp-password>
SMTP_FROM=noreply@yourdomain.com

# Image Storage
IMAGE_STORAGE_BUCKET=lumenai-images-prod
IMAGE_STORAGE_PROVIDER=s3  # or gcs

# Feature Flags (set to false in production)
ENABLE_DEV_AUTH=false
```

---

## Step 2 — Database Setup

### Initial Schema
On first startup, `Base.metadata.create_all()` creates all tables automatically for SQLite. For PostgreSQL, run the application once with a new database to trigger schema creation, then confirm:

```sql
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
```

Expected tables include: `inspections`, `baselines`, `instruments`, `capa_items`, `audit_logs`, `p25_instrument_identities`, and ~40 others.

### Phase 9 Migration (if upgrading from pre-Phase-9)
```sql
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS facility_name VARCHAR(255);
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS department VARCHAR(255);
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS tray_id VARCHAR(100);
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS instrument_barcode VARCHAR(255);
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS instrument_udi VARCHAR(255);
```

### Index Recommendations
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_tenant_id ON inspections(tenant_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_created_at ON inspections(created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_inspections_detected_issue ON inspections(detected_issue);
```

---

## Step 3 — Tenant Provisioning

Each hospital is a separate tenant. Provision via admin API or direct DB insert:

```python
# Via API (admin role required)
POST /api/admin/tenants
{
  "tenant_id": "bon-secours-pilot",
  "tenant_name": "Bon Secours Hospital",
  "facility_name": "Bon Secours Richmond",
  "plan": "hospital"
}
```

Or directly:
```sql
INSERT INTO tenants (tenant_id, tenant_name, plan, created_at)
VALUES ('bon-secours-pilot', 'Bon Secours Hospital', 'hospital', NOW());
```

---

## Step 4 — First Admin Account

API keys are issued once and stored as SHA-256 hash only:

```bash
# Generate a raw key
python3 -c "import secrets; print(secrets.token_urlsafe(40))"

# The raw key is shown ONCE — save it securely
# The system stores only the SHA-256 hash
```

Deliver the raw key to the customer admin via a secure channel (1Password Send, LastPass Share, or encrypted email).

---

## Step 5 — Frontend Deployment

```bash
# Build
npm --prefix frontend run build

# Environment variable required at build time
VITE_API_BASE_URL=https://api.yourdeployment.com

# Output
frontend/dist/  — upload to CDN / static host
```

No server-side rendering. All routes are client-side. Configure your CDN/host to serve `index.html` for all paths (SPA routing).

---

## Step 6 — Baseline Image Collection

Before the first production inspections, work with the customer's vendor to collect approved baseline images:

1. Vendor submits via `/vendor-baseline-portal`
2. SPD Manager reviews via `/baseline-review`
3. Target: ≥ 1 approved baseline per lumened scope type in fleet
4. Minimum: 1 approved baseline for the most common scope type before go-live

Reference: `docs/pilot/pilot-image-ingestion-guide.md`

---

## Step 7 — Inspection Collection

With baselines in place, the platform is ready for live inspections:

1. Technicians use `/inspection/new` after each instrument reprocessing
2. SPD Managers review findings via `/findings` (target: ≤ 8h turnaround)
3. Critical findings (risk score ≥ 80) should trigger immediate review
4. CAPAs created for confirmed critical findings

---

## Step 8 — Dashboard Usage

After 20+ inspections, the Dashboard and Executive Command Center become meaningful:

1. Dashboard (`/`) — contamination KPI grid, pilot metrics
2. Executive Command Center (`/executive-command-center`) — 16 KPIs for leadership
3. Surgical Readiness (`/surgical-readiness`) — composite readiness scoring
4. Instrument Passport (`/instrument-passport?instrument=[ID]`) — per-instrument lifecycle

---

## Step 9 — ROI Reporting

At 60 days post go-live:

1. Navigate to `/roi-center`
2. Review estimated time saved, findings detected, cost avoidance
3. Export CSV for QBR deck
4. Share with SPD Director and executive sponsor

---

## Step 10 — Executive Reviews

At 90 days:

1. Pull fresh ROI report
2. Run executive demo walkthrough (see `docs/demo/executive-demo-walkthrough.md`)
3. Review Customer Health Score at `/customer-success`
4. Begin renewal conversation

---

## Security Checklist Before Go-Live

- [ ] `ENABLE_DEV_AUTH=false` in production
- [ ] `SECRET_KEY` is 64+ chars, randomly generated, not committed to source control
- [ ] All admin API keys are SHA-256 hashed, raw key delivered securely
- [ ] Database connection string uses SSL (`sslmode=require`)
- [ ] No PHI in demo data or image metadata
- [ ] RBAC roles confirmed: admin, spd_manager, spd_technician, vendor, viewer
- [ ] Tenant isolation verified: log in as two tenants, confirm no data crossover
- [ ] Audit logging active: every inspection, approval, and CAPA creates an audit event

---

## Monitoring

### Health Check
```
GET /api/health
→ 200 OK {"status": "ok"}
```

### Key Metrics to Monitor
- API response time (p95 < 500ms)
- Inspection creation success rate (target 100%)
- Database connection pool utilization (alert > 80%)
- Storage usage growth rate

---

*LumenAI Engineering — Internal Use Only*  
*Do not commit secrets, API keys, or database credentials to source control.*  
*LumenAI makes no claim of FDA clearance or regulatory approval.*
