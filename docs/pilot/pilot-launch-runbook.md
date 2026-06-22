# LumenAI Pilot Launch Runbook

**Version:** 1.0  
**Effective Date:** 2026-06-21  
**Owner:** Pilot Operations Team  
**Audience:** LumenAI Customer Success, IT, and Site Coordinators

---

## 1. Pre-Launch Checklist (T-14 Days)

### 1.1 Infrastructure Readiness

- [ ] Backend API deployed to production environment (HTTPS only)
- [ ] `DATABASE_URL` configured for production PostgreSQL (not SQLite)
- [ ] `RATELIMIT_ENABLED=1` confirmed in production environment
- [ ] `VITE_API_BASE_URL` set correctly in frontend `.env.production`
- [ ] TLS certificate valid and auto-renewal configured
- [ ] Database backup job scheduled (nightly, offsite)
- [ ] APScheduler jobs verified: nightly intelligence sweep 00:30 UTC, global aggregation 02:00 UTC

### 1.2 Tenant Provisioning

- [ ] Pilot site tenant record created in database
- [ ] `tenant_id` and `tenant_name` confirmed with site coordinator
- [ ] Pilot admin user account created (role: `spd_manager`)
- [ ] Site SPD tech accounts created (role: `viewer`)
- [ ] Credentials delivered via secure channel (never email plaintext)
- [ ] Initial login tested by at least one site user

### 1.3 Data Agreements

- [ ] Business Associate Agreement (BAA) executed
- [ ] Data Processing Agreement (DPA) signed
- [ ] Pilot participation consent form distributed to site staff
- [ ] Data retention policy (90-day pilot period) acknowledged in writing
- [ ] Data destruction schedule agreed upon post-pilot

### 1.4 Integration Verification

- [ ] POST `/api/auth/token` — login endpoint responding
- [ ] GET `/api/inspections/{id}` — scoped to pilot tenant_id
- [ ] POST `/api/inspections/upload-images` — 10 MB limit enforced, SHA-256 hashing confirmed
- [ ] GET `/api/history/summary` — returning pilot tenant data only
- [ ] Cross-tenant isolation smoke test: pilot tenant cannot see other tenant records

### 1.5 Site Readiness

- [ ] Site network allows outbound HTTPS to LumenAI API endpoint
- [ ] At least 2 device types tested (tablet + desktop browser)
- [ ] Site IT contact documented for escalation
- [ ] Pilot coordinator trained (attended training session or completed self-guided guide)

---

## 2. Launch Day Checklist (Day 0)

**Start time:** 07:00 site local time (avoid shift change windows)

| Time | Action | Owner | Status |
|------|--------|-------|--------|
| T-60 min | Final API health check: `GET /api/health` | LumenAI Ops | |
| T-45 min | Confirm pilot coordinator on-site | CS Lead | |
| T-30 min | Walk first user through login at `/login` | CS Lead | |
| T-30 min | Submit one test inspection (mark `status: test`) | CS Lead + Coordinator | |
| T-15 min | Verify test inspection visible in history | CS Lead | |
| T-0 | Declare pilot live, begin real data collection | Both | |
| T+1 hr | Check-in call with coordinator | CS Lead | |
| T+4 hr | Confirm at least 5 inspections logged | CS Lead | |
| EOD | Summary email to site and internal stakeholders | CS Lead | |

### Launch Day Abort Criteria

Abort launch and escalate if:
- Login endpoint returns 5xx for >2 minutes
- Tenant isolation test fails (wrong tenant data visible)
- Fewer than 3 users successfully log in after 30 minutes of support

---

## 3. Daily Monitoring (Weeks 1–4)

### 3.1 Morning Check (08:00 UTC)

```
1. GET /api/health → expect 200
2. Check APScheduler logs for nightly job completion (00:30 UTC run)
3. Review error rate in application logs (target < 1% of requests)
4. Check DB disk usage (alert threshold: 80%)
```

### 3.2 Daily Metrics Review

Pull from `/api/history/summary` for pilot tenant:

| Metric | Target | Action if Below |
|--------|--------|-----------------|
| Inspections logged today | ≥ 5 | Contact coordinator |
| Inspections with all required fields | ≥ 95% | Review data quality report |
| API error rate | < 1% | Page on-call engineer |
| P95 response time | < 500 ms | Notify engineering |

### 3.3 Daily Standup Template

```
Date: ____
Inspections logged (last 24h): ____
Data quality issues flagged: ____
User issues reported: ____
Blocker for today: ____
```

---

## 4. Weekly Review (Every Friday)

### 4.1 Metrics Summary

- Total inspections logged (week and cumulative)
- Unique users active
- Data completeness rate (fields filled vs. required)
- Stain detection rate (% of inspections flagging stain_detected=true)
- User-reported errors or confusion points

### 4.2 Site Coordinator Call Agenda (30 min)

1. Review week's volume and quality numbers (10 min)
2. Surface any workflow friction (10 min)
3. Preview next week's focus (5 min)
4. Open Q&A (5 min)

### 4.3 Internal Review

- Engineering: any performance regressions?
- Product: any feature gaps surfaced by site?
- Legal/Compliance: any data handling concerns?

---

## 5. Escalation Contacts

| Issue Type | First Contact | Escalation |
|-----------|---------------|------------|
| API down / 5xx errors | On-call engineer (PagerDuty) | CTO within 15 min |
| Login / auth failure | CS Lead | On-call engineer |
| Data appearing in wrong tenant | On-call engineer (P0) | CTO + Legal immediately |
| User training question | CS Lead | Pilot coordinator |
| BAA / legal question | Legal counsel | CEO |
| Site IT network issue | Site IT contact | CS Lead |

**P0 Incident (Cross-Tenant Data Leak):**  
1. Immediately disable the affected tenant's API key  
2. Page CTO and Legal  
3. Preserve logs — do not delete or overwrite  
4. Notify site within 1 hour per BAA obligations  
5. Root cause analysis within 24 hours  

---

## 6. Data Export Process

### 6.1 Pilot Data Export (End of Pilot)

Pilot data export is performed by a LumenAI engineer with database access. Export scope is limited strictly to the requesting pilot tenant's `tenant_id`.

**Steps:**

```bash
# 1. Verify tenant_id to export
SELECT DISTINCT tenant_id FROM inspections WHERE tenant_id = '<pilot_tenant_id>' LIMIT 1;

# 2. Export inspections (CSV — no PHI fields included)
COPY (
  SELECT id, created_at, file_name, stain_detected, confidence,
         material_type, status, model_name, model_version,
         inference_timestamp, instrument_type, detected_issue,
         inference_mode, risk_score, vendor_name, site_name
  FROM inspections
  WHERE tenant_id = '<pilot_tenant_id>'
) TO '/tmp/pilot_export_<date>.csv' CSV HEADER;

# 3. Verify row count matches reported total
# 4. Encrypt export file before transmission: gpg --encrypt
# 5. Deliver via secure file transfer (not email)
# 6. Log export event in audit trail
```

### 6.2 Post-Pilot Data Destruction

Per signed DPA, pilot data is destroyed within 30 days of pilot end:

```sql
-- Requires dual approval (CS Lead + Engineer)
DELETE FROM inspections WHERE tenant_id = '<pilot_tenant_id>';
DELETE FROM users WHERE tenant_id = '<pilot_tenant_id>';
-- Confirm with: SELECT COUNT(*) FROM inspections WHERE tenant_id = '<pilot_tenant_id>';
```

Destruction certificate issued to site within 5 business days.

---

## 7. Go-Live Sign-Off

| Approver | Role | Signature | Date |
|---------|------|-----------|------|
| | CTO | | |
| | CS Lead | | |
| | Site Coordinator | | |
| | Legal Counsel | | |
