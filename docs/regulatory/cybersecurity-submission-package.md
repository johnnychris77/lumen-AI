# Cybersecurity Submission Package
**LumenAI SPD Intelligence Platform** | CSP-LUM-001 | Version 1.0-DRAFT
**Per FDA Cybersecurity in Medical Devices Guidance (September 2023)**
**Status**: In Review | **Subject to regulatory counsel and cybersecurity expert review before submission.**

---

## 1. Cybersecurity Management Plan

### 1.1 Scope
This Cybersecurity Submission Package covers the LumenAI SaaS platform version 1.0-RC, including all API endpoints, authentication systems, data storage, external integrations, and mobile/offline components.

### 1.2 Threat Modeling Methodology
LumenAI has applied the STRIDE threat modeling framework to all system components. Full threat model available at: docs/clinical/cybersecurity-threat-model.md

**STRIDE coverage**:
| Threat Category | Primary Mitigations |
|----------------|---------------------|
| **S**poofing | JWT authentication; bcrypt password hashing; anti-replay controls |
| **T**ampering | Append-only audit logs; immutable inspection records; TLS in transit |
| **R**epudiation | Comprehensive audit logging (all actions logged with user identity) |
| **I**nformation Disclosure | Tenant isolation; TLS encryption; secrets management |
| **D**enial of Service | Rate limiting (slowapi); infrastructure-level WAF |
| **E**levation of Privilege | RBAC; tier_guard middleware; require_enterprise_auth decorator |

### 1.3 Vulnerability Disclosure Policy
- **Disclosure contact**: security@lumenai.health (target; to be established)
- **Responsible disclosure period**: 90 days from private notification
- **Scope**: All LumenAI production endpoints and client-side code
- **Out of scope**: Third-party services not under LumenAI control
- **Safe harbor**: LumenAI commits to not pursuing legal action against researchers following responsible disclosure policy
- **Acknowledgment**: Researchers acknowledged in security advisory (with permission)

### 1.4 Patch Management Policy

| Severity | CVSS Score | Patch Target | Emergency Procedure |
|----------|-----------|-------------|---------------------|
| Critical | ≥ 9.0 | 30 days | Emergency release process; customer notification within 24h |
| High | 7.0–8.9 | 60 days | Standard release with priority; customer notification |
| Medium | 4.0–6.9 | 90 days | Next scheduled release |
| Low | < 4.0 | Next major release | Tracked in backlog |

### 1.5 Security Testing Cadence
| Activity | Tool / Method | Frequency | Status |
|---------|--------------|----------|--------|
| Static analysis | ruff (Python) | Every CI build | Active |
| Dependency vulnerability scan | pip-audit (planned) | Weekly (target) | Gap — not yet in CI |
| DAST | OWASP ZAP (planned) | Pre-release | Gap — not yet implemented |
| Penetration test | CREST/OSCP firm (planned) | Annual | Gap — not yet completed |
| Container scan | Trivy (planned) | Every CI build | Gap — not yet in CI |
| Secrets scan | git-secrets / trufflehog (planned) | Every CI commit | Gap — not yet in CI |

---

## 2. Security Architecture

### 2.1 Authentication

| Mechanism | Implementation | Scope |
|-----------|---------------|-------|
| JWT Bearer Token | Python-jose; HS256 (RS256 planned) | All /api/ routes |
| Dev Token Bypass | DEV_TOKEN env var — non-production ONLY | Dev/test environments |
| Enterprise Auth | enterprise_auth module; enhanced validation | Enterprise tier routes |
| Session Expiry | Configurable JWT expiry (default: 24 hours) | All users |
| Refresh Tokens | Planned — not yet implemented | Gap |
| MFA | Planned — not yet implemented | Gap (enterprise priority) |

**Critical**: DEV_TOKEN bypass must not be enabled in production. This is enforced through deployment checklist and startup validation. See docs/regulatory/risk-management-addendum-p19.md §P19-008.

### 2.2 Authorization (RBAC)

| Role | Access Level | Primary Functions |
|------|-------------|------------------|
| technician | Own tenant, standard routes | Inspection CRUD, image capture |
| supervisor | Own tenant, team oversight | Review findings, approve dispositions |
| manager | Own tenant, management routes | Reports, quality trends |
| enterprise | Enterprise routes (Zone 3) | Executive dashboard, network intelligence |
| admin | Cross-tenant admin (Zone 4) | Tenant management, audit log access |

**Enforcement**: `tier_guard` middleware and `require_enterprise_auth` decorator applied to all Zone 3/4 routes. Role claims verified from JWT on every request.

### 2.3 Tenant Isolation

Multi-layer tenant isolation (see software-architecture-package.md §5 for full detail):
- JWT contains tenant_id claim (verified on every request)
- All SQLAlchemy queries filtered by tenant_id at ORM layer
- No cross-tenant joins exist in codebase
- Network intelligence uses pseudonymized cohorts only (no facility identifiers)
- Audit log captures all cross-tenant admin access

### 2.4 Encryption in Transit

| Connection | Protocol | Configuration |
|-----------|---------|--------------|
| Browser ↔ Nginx | TLS 1.2+ | Configured in frontend/nginx.conf |
| Nginx ↔ FastAPI | HTTP (internal) | Within container network; TLS at boundary |
| FastAPI ↔ PostgreSQL | TLS (production) | RDS SSL mode required |
| Mobile ↔ Backend | TLS 1.2+ via same Nginx | Same as browser |

**TLS Configuration** (nginx.conf):
- `ssl_protocols TLSv1.2 TLSv1.3;`
- `ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:...` (strong cipher suite)
- HSTS header included: `Strict-Transport-Security: max-age=31536000; includeSubDomains`

### 2.5 Encryption at Rest

| Data | Mechanism | Implementation |
|------|-----------|---------------|
| PostgreSQL database | AES-256 (cloud provider managed) | AWS RDS encryption at rest |
| Application secrets | Environment variables / AWS Secrets Manager | Never in source code |
| Docker images | Build-time — no secrets baked in | Verified in CI |
| Local dev SQLite | Not encrypted | Dev environment only; no production data |
| Offline IndexedDB | Browser-managed encryption | Platform dependent (iOS 16+ encrypted) |

**Gap**: Field-level encryption for particularly sensitive fields not implemented.

### 2.6 API Security Controls

| Control | Implementation | Status |
|---------|---------------|--------|
| Rate limiting | slowapi (RATELIMIT_ENABLED=1 required) | Active (requires env var) |
| CORS policy | Nginx/FastAPI CORS middleware | Active |
| CSP headers | Nginx Content-Security-Policy | Configured in nginx.conf |
| X-Frame-Options | Nginx DENY | Configured |
| X-Content-Type-Options | Nginx nosniff | Configured |
| Input validation | Pydantic models on all request bodies | Active |
| SQL injection prevention | SQLAlchemy ORM (parameterized queries) | Active |
| XSS prevention | React default escaping + CSP | Active |

---

## 3. Software Bill of Materials (SBOM) Strategy

### 3.1 SBOM Format
Target formats: CycloneDX 1.4 (primary) or SPDX 2.3 (alternative)
Per FDA 2023 Cybersecurity Guidance recommendation.

### 3.2 SBOM Generation Plan

**Backend (Python)**:
```bash
pip install cyclonedx-bom
cyclonedx-py requirements backend/requirements.txt -o sbom-backend.json --format json
```

**Frontend (JavaScript/TypeScript)**:
```bash
npm install -g @cyclonedx/cyclonedx-npm
cyclonedx-npm --package-lock-only -o sbom-frontend.json
```

**Combined SBOM**: Merge using CycloneDX merge tooling.

### 3.3 Key Dependencies Inventory (Manual — SBOM Generation Pending)

**Backend**:
| Package | Version (approx) | Security Notes |
|---------|-----------------|---------------|
| FastAPI | 0.100+ | Regular security updates; actively maintained |
| SQLAlchemy | 2.x | ORM; parameterized queries prevent SQLi |
| APScheduler | 3.x | Background jobs; no network exposure |
| slowapi | 0.1.x | Rate limiting; well-maintained |
| Pydantic | 2.x | Input validation; actively maintained |
| python-jose | 3.x | JWT; HS256/RS256 |
| bcrypt | 4.x | Password hashing |
| uvicorn | 0.20+ | ASGI server; production: behind Nginx |
| alembic | 1.x | DB migrations; no runtime network exposure |

**Frontend**:
| Package | Version (approx) | Security Notes |
|---------|-----------------|---------------|
| React | 18.x | XSS prevention via JSX; actively maintained |
| Vite | 5.x | Build tool only; no runtime exposure |
| TypeScript | 5.x | Build time only |

### 3.4 SBOM Distribution
- SBOM provided to customers upon request
- SBOM included in FDA submission package (machine-readable)
- SBOM updated with each release

### 3.5 Gap
**Automated SBOM generation is not yet integrated into CI pipeline.** This is a pre-submission gap. Target: automated generation on every release build (P20).

---

## 4. Vulnerability Management

### 4.1 Current Vulnerability Management

| Activity | Tool | Status |
|---------|------|--------|
| Static code analysis | ruff | Active — every CI build |
| Manual dependency review | Manual audit | Ad hoc |
| GitHub Dependabot | Not yet configured | Gap |
| pip-audit | Not yet in CI | Gap |
| npm audit | Not yet in CI | Gap |
| OWASP Dependency-Check | Not yet implemented | Gap |
| Container scanning | Not yet implemented | Gap |

### 4.2 Known Vulnerability Remediation Process
1. Vulnerability identified (manual review, security advisory, or future automated scan)
2. CVSS score assessed
3. Patch timeline assigned per §1.4 policy
4. Patch developed and tested per standard PR process
5. Release cut if severity warrants expedited release
6. Customer notification per severity tier
7. Incident documented in vulnerability registry

### 4.3 Pre-Submission Gaps

| Gap | Priority | Action |
|-----|----------|--------|
| No automated dependency scanning in CI | HIGH | Integrate pip-audit and npm audit |
| No Dependabot configuration | HIGH | Add .github/dependabot.yml |
| No completed penetration test | CRITICAL | Engage CREST/OSCP firm (6–12 months before submission) |
| No DAST (OWASP ZAP) | HIGH | Integrate into staging pipeline |
| No container vulnerability scanning | MEDIUM | Add Trivy to CI |
| No secrets scanning in CI | HIGH | Add git-secrets or trufflehog |

---

## 5. Audit Logging

### 5.1 Audit Log Content

Every user action generates an audit log entry with:
- `tenant_id` — tenant context
- `user_id` — authenticated user
- `action_type` — action category (e.g., INSPECTION_SUBMIT, FINDING_CONFIRM, FINDING_OVERRIDE)
- `resource_id` — target resource (inspection_id, finding_id, etc.)
- `timestamp` — UTC ISO 8601
- `ip_address` — source IP address
- `user_agent` — browser/client identifier
- `status` — success or failure

### 5.2 Audit Log Security Controls
- Audit logs are **append-only** — no DELETE API is exposed for audit records
- Audit log table has no UPDATE operations in ORM
- Admin access to audit logs is itself audited (Zone 4)
- Logs retained in database; export to immutable storage planned

### 5.3 Retention Policy
| Tier | Retention Period |
|------|----------------|
| Starter | 1 year |
| Professional | 3 years |
| Enterprise | 7 years |

Retention policy enforced via APScheduler archival job.

---

## 6. Incident Response Plan

### 6.1 Severity Classification
| SEV | Trigger | Response Time | Notification |
|-----|---------|--------------|-------------|
| SEV1 | Patient safety impact; PHI breach; service-wide outage | 1 hour | Immediate — CEO, regulatory, legal |
| SEV2 | Single-tenant data exposure; significant service degradation | 4 hours | Within 2 hours of confirmation |
| SEV3 | Non-patient-safety feature unavailability; minor data issue | 24 hours | Within 8 hours |
| SEV4 | Low-impact bug; cosmetic issue | Next business day | Next maintenance window |

### 6.2 Breach Notification
- HIPAA Breach Notification Rule: affected customers notified within 72 hours of confirmed breach determination
- If > 500 individuals affected: HHS notification required
- State breach notification laws: vary by state; legal counsel to advise
- FDA MDR: if breach causes or may cause serious injury, MDR may be required

### 6.3 Incident Response Steps
1. **Detect**: Monitoring alert or user report
2. **Contain**: Isolate affected system/tenant; revoke compromised credentials
3. **Assess**: Determine scope, patient safety impact, PHI exposure
4. **Notify**: Per SEV level and regulatory requirements
5. **Remediate**: Patch, configuration change, or architectural fix
6. **Review**: Post-incident analysis; update threat model
7. **Document**: Incident report; regulatory filing if required

Reference: docs/platform/security-operations.md (if exists)

---

## 7. FDA 2023 Cybersecurity Guidance Mapping

| FDA Guidance Recommendation | LumenAI Control | Status |
|----------------------------|-----------------|--------|
| Cybersecurity management plan | This document §1 | Complete (plan); gaps in execution |
| Threat modeling | STRIDE model; docs/clinical/cybersecurity-threat-model.md | Complete |
| SBOM (machine-readable) | CycloneDX/SPDX planned | Gap — not yet generated |
| Vulnerability disclosure policy | §1.3 | Plan established; implementation pending |
| Patch management policy | §1.4 | Policy defined |
| Security architecture documentation | §2 (this document) | Complete |
| Authentication controls | JWT; bcrypt; enterprise_auth | Complete (MFA gap) |
| Authorization controls | RBAC; tier_guard | Complete |
| Encryption in transit | TLS 1.2+ via Nginx | Complete |
| Encryption at rest | Cloud provider AES-256 | Partial (field-level gap) |
| Audit logging | Append-only; comprehensive | Complete |
| Security testing (SAST) | ruff (limited) | Partial — ruff is linter, not security-focused SAST |
| Security testing (DAST) | Not yet implemented | Gap |
| Penetration testing | Not yet completed | Gap — critical pre-submission |
| Post-market monitoring | kappa-monitor; /metrics endpoint | Partial |
| Incident response | §6 (this document) | Plan established; process formalization needed |
| Cybersecurity labeling | user-labeling-and-instructions.md | Partial |
| Total product lifecycle (TPLC) approach | AI-ML change control plan; PCCP | Complete |

**Overall FDA Guidance Compliance Level**: Partially Ready
**Critical Pre-Submission Actions**: Penetration test, SBOM generation, DAST implementation, automated vulnerability scanning.

---

*Document Owner: Cybersecurity Lead + Regulatory Affairs Lead*
*Review Cycle: Annual + post-incident | Next Review: 2027-06-21*
*This document does not constitute regulatory clearance or security certification.*
