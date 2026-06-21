# LumenAI Pilot Data Governance Policy

**Version:** 1.0  
**Effective Date:** 2026-06-21  
**Owner:** Legal & Compliance  
**Review Cycle:** Quarterly  

---

## 1. Purpose and Scope

This policy governs how LumenAI collects, processes, stores, and destroys data during the pilot program. It applies to:
- All pilot site participants (hospitals, SPD facilities)
- All LumenAI staff with access to pilot data
- All systems processing pilot data

---

## 2. Data Classification

| Class | Examples | Handling |
|-------|---------|---------|
| Instrument Quality Data | Inspection records, stain detections, findings | Encrypted at rest and in transit; tenant-scoped access only |
| Baseline Reference Data | Vendor-submitted reference images (SHA-256 hash only) | Same as above |
| Authentication Data | User emails, hashed passwords, JWT tokens | Never logged; tokens expire per session |
| Aggregate Intelligence | Cross-tenant signals (anonymized, k≥10) | No individual tenant identifiable |
| Audit Logs | API calls, data access events | Retained 7 years; immutable |

**Data NOT Collected:**
- Patient names, identifiers, or PHI of any kind
- Raw images (only SHA-256 hash stored)
- Staff personal information beyond work email
- Financial or billing data

---

## 3. Tenant Data Isolation

**Principle:** No tenant can access another tenant's raw data under any circumstances.

**Enforcement mechanisms:**
- All inspection queries filter by `tenant_id` derived from the authenticated JWT
- Admin role users (LumenAI staff only) are the sole exception — with access logged
- Cross-tenant intelligence (P15+) uses k-anonymized aggregates only; individual tenant data is never exposed
- Database-level: row-level tenant_id column on all data tables
- API-level: `get_request_tenant_id(request)` applied on every relevant route
- Test suite includes cross-tenant isolation smoke tests (must pass on every deploy)

**Violation response:** Any confirmed cross-tenant data exposure is a P0 security incident triggering immediate containment, notification within 1 hour, and root cause analysis within 24 hours.

---

## 4. Data Retention

| Data Type | Retention Period | Basis |
|-----------|----------------|-------|
| Inspection records | Pilot period + 30 days | DPA agreement |
| Audit logs | 7 years | Regulatory best practice |
| Authentication tokens | Session duration only | Security requirement |
| Image hashes (SHA-256) | Pilot period + 30 days | Same as inspection records |
| Aggregate intelligence signals | 12 months | Product operation |
| Consent records | Duration of consent + 5 years | GDPR Article 7 |

---

## 5. Data Access Controls

### 5.1 Role-Based Access

| Role | Data Access |
|------|------------|
| `viewer` | Own-tenant inspection records only |
| `spd_manager` | All own-tenant inspection records + findings |
| `admin` (LumenAI staff) | All tenant data for support/ops; all access logged |

### 5.2 Access Logging

Every API request is logged with:
- Timestamp (UTC)
- User identifier (email)
- Tenant ID
- Endpoint accessed
- HTTP status returned

Logs are stored immutably and retained 7 years.

### 5.3 Privileged Access

LumenAI database access requires:
- Dual approval (engineer + manager)
- Recorded in access log
- Specific tenant scope documented before access
- Access session recorded

---

## 6. Data Minimization

LumenAI collects only data necessary for the stated purpose (instrument quality analysis):
- No patient data — by design
- Images not stored — SHA-256 hash only
- Free-text fields have character limits to reduce PHI risk
- Pilot data fields reviewed quarterly; any field not demonstrably useful is removed

---

## 7. Data Subject Rights

For personal data of system users (work email, login activity):

| Right | How to Exercise | Response Time |
|-------|---------------|--------------|
| Access (GDPR Art. 15) | Email privacy@lumenai.com | 30 days |
| Rectification (GDPR Art. 16) | Email privacy@lumenai.com | 30 days |
| Erasure (GDPR Art. 17) | Email privacy@lumenai.com | 30 days (subject to audit log retention) |
| Portability (GDPR Art. 20) | Email privacy@lumenai.com | 30 days |

Instrument quality data (inspection records) is organizational data, not personal data, and is not subject to individual data subject requests. It is governed by the BAA and DPA between LumenAI and the site.

---

## 8. Security Requirements

- All data in transit: TLS 1.2 minimum (TLS 1.3 preferred)
- All data at rest: AES-256 encryption
- Passwords: bcrypt-hashed, never stored in plaintext
- JWT tokens: short-lived (configurable, default 8 hours), HTTPS-only
- No hardcoded credentials in application code
- Secrets managed via environment variables only (never committed to source control)
- Rate limiting enabled in production (`RATELIMIT_ENABLED=1`)

---

## 9. Third-Party Data Sharing

**During the pilot, data is NOT shared with:**
- Other hospitals or facilities (except as k-anonymized aggregates with k≥10 and only with DPA in place)
- Regulatory bodies (data is for quality improvement, not regulatory submission)
- Marketing or advertising platforms
- AI model training services outside LumenAI's own infrastructure

**Data sharing requires:**
- Written approval from site data steward
- Updated DPA if sharing extends beyond original scope
- Audit event created for every sharing action

---

## 10. Incident Response

### 10.1 Data Breach Classification

| Severity | Definition | Notification Timeline |
|----------|-----------|----------------------|
| P0 — Critical | Cross-tenant data exposure; confirmed unauthorized access | Site notified within 1 hour; regulatory notification per applicable law |
| P1 — High | Potential unauthorized access; credential compromise | Site notified within 4 hours |
| P2 — Medium | Access anomaly under investigation | Site notified within 24 hours if confirmed |

### 10.2 Breach Response Steps

1. **Contain** — disable affected credentials or endpoints immediately
2. **Preserve** — do not delete logs; snapshot affected state
3. **Assess** — determine scope of exposure
4. **Notify** — site and regulatory bodies per timeline above
5. **Remediate** — fix root cause
6. **Report** — written incident report within 5 business days

---

## 11. Governance Roles

| Role | Responsibility |
|------|--------------|
| Data Controller | Pilot site (hospital) — controls purpose of instrument data |
| Data Processor | LumenAI — processes data on behalf of controller |
| Data Protection Officer | LumenAI Legal counsel (contact: legal@lumenai.com) |
| Site Data Steward | Designated site coordinator |
| Pilot Data Trustee | LumenAI CS Lead |

---

## 12. Policy Review and Updates

This policy is reviewed:
- At the start of each pilot cohort
- Following any P0 or P1 security incident
- When applicable regulations change
- At minimum, quarterly

Changes require sign-off from LumenAI Legal and the affected site's data steward.
