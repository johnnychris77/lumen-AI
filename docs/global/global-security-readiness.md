# Global Security Readiness — LumenAI International

**Document ID:** LUM-GLOBAL-008  
**Version:** 1.0  
**Status:** Planning  
**Milestone:** P20 — International Expansion & Global Regulatory Readiness  
**Classification:** Security Confidential  

> **Note:** This document references existing security controls established in P0–P19 milestones and maps them to international requirements. No security controls are weakened or removed. All gaps identified represent additive hardening requirements for international market entry.

---

## 1. Executive Summary

LumenAI's security foundation — established across P0–P19 milestones — provides a strong baseline for international market entry. This document validates the current security posture against international requirements across eight key dimensions and identifies additive certification, testing, and process requirements for each target market.

**Overall International Security Readiness: CONDITIONALLY READY**

Core technical security controls (encryption, isolation, access control, audit logging) meet international requirements. Gap areas are primarily certifications (ISO 27001, Cyber Essentials Plus, IRAP) and international-scope penetration testing that must be layered on top of the existing US-compliant posture.

---

## 2. Security Posture Validation

### 2.1 Encryption

**Current Status: ACTIVE — MEETS INTERNATIONAL REQUIREMENTS**

| Control | Standard | Implementation | Status | Markets Covered |
|---------|----------|----------------|--------|-----------------|
| Data at rest | AES-256 | AWS KMS with Customer Managed Keys; RDS encryption enabled; S3 SSE-KMS | ACTIVE | All markets |
| Data in transit | TLS 1.2+ | All API endpoints enforce TLS 1.2 minimum; TLS 1.3 enabled where supported | ACTIVE | All markets |
| Key management | FIPS 140-2 | AWS KMS FIPS 140-2 Level 2 validated HSMs | ACTIVE | All markets |
| Database column encryption | Application-level | PHI fields additionally encrypted at application layer (beyond RDS encryption) | ACTIVE | All markets |
| Backup encryption | AES-256 | RDS automated backups encrypted with CMK | ACTIVE | All markets |

**Alignment to International Standards:**
- GDPR (Article 32): Encryption explicitly referenced as appropriate technical measure — SATISFIED
- UK GDPR: Same as GDPR — SATISFIED
- PIPEDA: Encryption as security safeguard — SATISFIED
- Australian Privacy Act (APP 11): Reasonable steps to protect — encryption satisfies — SATISFIED
- PDPA Singapore: Security arrangements — AES-256/TLS satisfies — SATISFIED
- ISO 27001 (Control A.10): Cryptographic controls — satisfies ISO 27001 control requirements — SATISFIED
- HIPAA Security Rule (164.312(e)(2)): Encryption and decryption — satisfies — SATISFIED

**No gaps identified in encryption controls.**

---

### 2.2 Key Management

**Current Status: ACTIVE — MEETS INTERNATIONAL REQUIREMENTS**

| Control | Implementation | Status | Notes |
|---------|----------------|--------|-------|
| Per-tenant encryption keys | AWS KMS CMK per tenant (tenant_id in key policy) | ACTIVE | Tenant key isolation maintained |
| Key rotation | Automatic annual rotation (AWS KMS managed) | ACTIVE | Satisfies NIST SP 800-57 guidance |
| Key access logging | CloudTrail logs all KMS key usage | ACTIVE | Audit trail for key access |
| Key deletion protection | 7-day minimum pending deletion window | ACTIVE | Prevents accidental key loss |
| Cross-region key policy | Regional KMS keys; no cross-region key sharing | PLANNED | Required for data sovereignty |
| Hardware Security Module | AWS KMS FIPS 140-2 L2 HSMs | ACTIVE | Hardware-backed key storage |

**International Extension Required:**
- Regional KMS key hierarchy: Each target region (EU, UK, CA, AU, SG) requires independent regional CMK hierarchy
- Status: PLANNED — activation per region at launch
- IRAP (Australia): Australian government data requires IRAP-assessed key management; AWS Australia IRAP assessed — SATISFIES

---

### 2.3 Tenant Isolation

**Current Status: ACTIVE — MEETS INTERNATIONAL REQUIREMENTS**

| Control | Implementation | Status |
|---------|----------------|--------|
| Row-level multi-tenancy | PostgreSQL Row-Level Security (RLS) with `tenant_id` enforcement | ACTIVE |
| Application-layer enforcement | All queries include `tenant_id` filter; enforced in ORM layer | ACTIVE |
| JWT tenant binding | `tenant_id` + `tenant_region` in all JWT claims | ACTIVE |
| API-level enforcement | Middleware rejects requests where JWT tenant_id ≠ resource tenant_id | ACTIVE |
| Storage isolation | Per-tenant S3 path prefix (or dedicated bucket for enterprise) | ACTIVE |
| Network isolation | VPC per environment; security groups restrict inter-service traffic | ACTIVE |
| Regional enforcement | `tenant_region` in JWT + API gateway regional routing enforcement | PLANNED |

**Validation:** Tenant isolation architecture satisfies GDPR data controller isolation requirements, UK GDPR, HIPAA multi-tenancy guidance, and equivalent frameworks.

**No gaps in core tenant isolation. Regional routing enforcement is the only additive requirement (in planning).**

---

### 2.4 Data Sovereignty Controls

**Current Status: PLANNING — REGIONAL ACTIVATION REQUIRED**

| Control | Requirement | Status |
|---------|-------------|--------|
| Regional data plane separation | Separate AWS stacks per region; no PHI cross-region | PLANNED |
| S3 bucket geo-restriction policies | Bucket policies restricting access to regional AWS endpoints | PLANNED |
| RDS regional isolation | No cross-region RDS replication for PHI databases | PLANNED |
| SCP (Service Control Policies) | AWS Organization SCPs preventing PHI bucket cross-region replication | PLANNED |
| Tenant-region binding enforcement | API middleware rejects misrouted requests | PLANNED |
| Data residency attestation | Customer-facing data residency commitment in DPA/BAA | IN PREPARATION |

**Gap Assessment:** All data sovereignty controls are architecturally designed (LUM-GLOBAL-005) but require activation per region at launch. This represents a PLANNED state, not a gap in architecture.

**Action:** Terraform IaC per region to be applied at launch sequencing per LUM-GLOBAL-005.

---

### 2.5 Regional Compliance Certifications

#### 2.5.1 ISO 27001

| Attribute | Detail |
|-----------|--------|
| **Standard** | ISO/IEC 27001:2022 (Information Security Management System) |
| **Markets Requiring** | EU (strong expectation for EU MDR NB assessment), UK (NHS preferred/required), AU (public sector), Singapore (CSA preferred), South Korea (MFDS expectation), global enterprise expectation |
| **Current Status** | NOT CERTIFIED — SOC 2 Type II in pursuit (structural overlap ~60–70%) |
| **Timeline to Certification** | 6–12 months from formal program initiation (readiness assessment → gap remediation → Stage 1 audit → Stage 2 audit → certification) |
| **Body** | BSI, Bureau Veritas, SGS, TÜV SÜD (UKAS/DAkkS accredited) |
| **Priority** | HIGH — required before EU/UK enterprise sales; strongly expected by all international markets |
| **Action** | Initiate ISO 27001 readiness assessment Q1 Year 1; target certification by Q4 Year 1 |

#### 2.5.2 SOC 2 Type II

| Attribute | Detail |
|-----------|--------|
| **Standard** | AICPA SOC 2 — Trust Service Criteria (Security, Availability, Confidentiality) |
| **Markets Requiring** | US (primary requirement), Canada, Australia, Singapore (commonly requested) |
| **Current Status** | IN PROGRESS (P19 milestone) |
| **Timeline** | 6–9 months audit period; Type II report for 6-month observation window |
| **Priority** | HIGH — US and Tier 1 international markets |

#### 2.5.3 Cyber Essentials Plus (UK)

| Attribute | Detail |
|-----------|--------|
| **Standard** | NCSC (National Cyber Security Centre) Cyber Essentials Plus |
| **Markets Requiring** | UK — required for NHS contracts (NHS DSP Toolkit references; NHS Supply Chain requirement) |
| **Scope** | Five control categories: Firewalls, Secure configuration, User access control, Malware protection, Patch management |
| **Current Status** | NOT CERTIFIED |
| **Timeline** | 4–6 weeks (Cyber Essentials) + 2–4 weeks for Plus (on-site/remote assessment) |
| **Priority** | HIGH — required for NHS commercial engagement |
| **Action** | Initiate Cyber Essentials assessment Q2 Year 1 (before UK commercial launch) |
| **Certifying Body** | IASME Consortium member; CREST-approved certification body |

#### 2.5.4 IRAP (Australia)

| Attribute | Detail |
|-----------|--------|
| **Standard** | Information Security Registered Assessors Program (Australian Signals Directorate) |
| **Markets Requiring** | Australia — government health data (State health department hospitals processing government health data) |
| **Scope** | Assessment of cloud infrastructure against Australian Government Information Security Manual (ISM) |
| **Applicability** | Required for Australian Government contracts; state health authority hospitals may require |
| **Current Status** | NOT ASSESSED — AWS ap-southeast-2 is IRAP-assessed (infrastructure covered); LumenAI application layer assessment needed |
| **Timeline** | 3–6 months (IRAP assessor engagement, assessment, reporting) |
| **Priority** | MEDIUM — required for public hospital sector in AU; less critical for private hospital |
| **Action** | Engage IRAP assessor Q3 Year 1 (concurrent with AU launch preparation) |
| **Note** | AWS Australia (ap-southeast-2) holds IRAP Protected assessment; LumenAI builds on IRAP-assessed infrastructure |

#### 2.5.5 CSA STAR (Singapore)

| Attribute | Detail |
|-----------|--------|
| **Standard** | Cloud Security Alliance STAR (Security, Trust, Assurance and Risk) Registry |
| **Markets Requiring** | Singapore — CSA Singapore recommends CSA STAR for cloud service providers; considered in GeBIZ procurement |
| **Current Status** | NOT REGISTERED |
| **Timeline** | CSA STAR Level 1 (self-assessment): 4–8 weeks to complete CAIQv4; Level 2 (third-party audit): 3–6 months |
| **Priority** | MEDIUM — Singapore market; Level 1 self-assessment is quick win |
| **Action** | Complete CSA STAR Level 1 self-assessment Q2 Year 1; Level 2 in Year 2 |

#### 2.5.6 DSP Toolkit (UK NHS)

| Attribute | Detail |
|-----------|--------|
| **Standard** | NHS Data Security and Protection (DSP) Toolkit — annual self-assessment |
| **Markets Requiring** | UK NHS — mandatory for organizations accessing NHS patient data |
| **Current Status** | NOT REGISTERED |
| **Timeline** | Annual registration; self-assessment 4–8 weeks for initial completion |
| **Priority** | HIGH — required for NHS data access |
| **Action** | Register and complete DSP Toolkit Q2 Year 1 |

---

### 2.6 Penetration Testing — International Scope

**Current Status: US-SCOPE ONLY — INTERNATIONAL EXTENSION REQUIRED**

| Requirement | Detail |
|-------------|--------|
| Current state | Annual penetration test — US-focused, US-based assessor |
| UK/EU/AU requirement | CREST-certified penetration testing organization required |
| CREST | Council of Registered Ethical Security Testers — accreditation recognized in UK (NCSC), EU, AU, SG |
| Scope extension | International regional endpoints, regional API gateways, cloud infrastructure in each region |
| Frequency | Annual minimum; semi-annual for high-risk components |

**CREST-Certified Testing Firms:**
- NCC Group (UK, global)
- Pen Test Partners (UK)
- Bishop Fox (US, CREST-certified)
- CyberCX (Australia)
- KPMG Cyber (Singapore, AU, UK)

**Action Plan:**
- Engage CREST-certified assessor Q3 Year 1 for UK launch pre-assessment
- Scope to include: UK regional API endpoints, AWS eu-west-2 infrastructure, UKCA submission security documentation
- Annual CREST penetration test to cover all active international regions
- Penetration test report available as evidence for:
  - NHS DSP Toolkit (penetration testing evidence required)
  - EU MDR NB assessment (cybersecurity evidence)
  - ISO 27001 certification (penetration testing as evidence of A.12.6 control)

---

### 2.7 Vulnerability Management

**Current Status: ACTIVE (GITHUB DEPENDABOT + MANUAL REVIEW)**

| Control | Current State | International SLA Requirement |
|---------|---------------|-------------------------------|
| Dependency scanning | GitHub Dependabot — automated PR for vulnerable dependencies | CVE CRITICAL (CVSS ≥ 9.0): 24 hours remediation target |
| Container scanning | AWS ECR image scanning on push | CVE HIGH (CVSS 7.0–8.9): 7 days remediation target |
| Static code analysis | Ruff (Python linting + security rules) | CVE MEDIUM (CVSS 4.0–6.9): 30 days |
| SAST | Bandit for Python security analysis | CVE LOW (CVSS < 4.0): 90 days |
| DAST | Not currently implemented | Planned — OWASP ZAP integration |
| CVE/NVD monitoring | GitHub Advisory Database via Dependabot | Manual supplement for non-GitHub-indexed CVEs |
| Patch SLA tracking | Manual tracking | Formalized SLA tracking required for ISO 27001 |

**International SLA Requirements:**

| Framework | Critical | High | Medium | Low |
|-----------|----------|------|--------|-----|
| GDPR / NHS DSP Toolkit | 24–72 hours | 7 days | 30 days | 90 days |
| ISO 27001 | 24–72 hours | 7 days | 30 days | 90 days |
| Australian Privacy Act | No explicit SLA; "reasonable steps" | As above | As above | As above |
| PDPA Singapore | No explicit SLA; reasonable | As above | As above | As above |
| SOC 2 | Consistent with above | As above | As above | As above |

**Action:** Formalize SLA tracking in JIRA; automated reporting for SLA compliance; add DAST (OWASP ZAP in CI/CD pipeline) by Q2 Year 1.

---

### 2.8 Incident Response — International Breach Notification

**Current Status: US HIPAA BREACH NOTIFICATION PROCESS ACTIVE — INTERNATIONAL EXTENSION REQUIRED**

#### 2.8.1 Breach Notification Requirements by Jurisdiction

| Jurisdiction | Regulator | Notification Timeline | Data Subject Notification | LumenAI Role |
|-------------|-----------|----------------------|--------------------------|--------------|
| HIPAA (US) | HHS OCR | 60 days (covered entity); BA notifies CE without unreasonable delay | If affecting 500+ individuals in a state | Business Associate |
| GDPR (EU) | National DPA (e.g., DPC Ireland, BfDI Germany) | 72 hours from processor awareness → controller notifies authority | Without undue delay if high risk | Data Processor |
| UK GDPR | ICO | 72 hours from controller awareness; processor notifies controller ASAP | Without undue delay if high risk | Data Processor |
| PIPEDA (CA) | OPC (national); CAI (Quebec) | ASAP to OPC; variable by province | If real risk of significant harm | Service Provider |
| Quebec Law 25 | Commission d'accès à l'information (CAI) | "As soon as reasonably possible"; 60 days guidance | If serious injury risk | Service Provider |
| Australian Privacy Act | OAIC | As soon as practicable; ~30 days | If serious harm | Service Provider |
| PDPA Singapore | PDPC | 3 calendar days (significant breach); 30 days (non-significant) | If significant harm | Data Processor |
| UAE PDPL | UAE Data Office | 72 hours | If risk of harm | Data Processor |
| Saudi PDPL | SDAIA | 72 hours | If risk of harm | Data Processor |

#### 2.8.2 International Incident Response Runbook Additions

**Current Gap:** US-only incident response runbook; no international breach notification procedures.

**Required Additions:**
1. **Multi-jurisdiction breach assessment matrix** — determine which authorities must be notified based on affected tenant regions
2. **Per-jurisdiction notification templates** — pre-approved templates in required languages (English primary; German for GDPR/BfDI; French for Quebec CAI; Arabic summary for UAE/Saudi)
3. **72-hour response capability** — GDPR, UK GDPR, UAE PDPL, Saudi PDPL all require 72-hour notification; current HIPAA process (60 days for covered entity) is less time-critical; procedures must support faster international timelines
4. **Regional Data Protection Officer contacts** — DPO/privacy officer contact for each jurisdiction
5. **Severity classification criteria** — consistent cross-jurisdiction breach severity assessment matrix
6. **Customer notification workflow** — customer (data controller) must be notified before regulatory authority in processor-controller relationship

**Action:** Update Incident Response Plan by Q2 Year 1 to include international breach notification runbook for all Tier 1 target markets.

---

## 3. Security Certification Roadmap

### 3.1 Priority Sequencing

```
Q1 Year 1:  ISO 27001 readiness assessment + gap remediation start
            SOC 2 Type II observation period (in progress from P19)
            DSP Toolkit registration (UK launch prep)
            CSA STAR Level 1 self-assessment (Singapore)

Q2 Year 1:  Cyber Essentials Plus (UK)
            SOC 2 Type II report completion
            CREST penetration test engagement (UK/international scope)
            International incident response runbook completion

Q3 Year 1:  ISO 27001 Stage 1 audit
            IRAP assessor engagement (Australia)
            CREST penetration test execution

Q4 Year 1:  ISO 27001 Stage 2 audit + certification target
            IRAP assessment report
            Annual penetration test report (international scope)

Q1 Year 2:  EU GDPR-specific DPIA completion
            CSA STAR Level 2 (Singapore)
            ISO 27001 surveillance audit
            Korea — PIPA security compliance review
```

### 3.2 Certification Summary Table

| Certification | Markets | Priority | Target | Status |
|--------------|---------|----------|--------|--------|
| SOC 2 Type II | US, CA, AU, SG | CRITICAL | Q3 Year 1 | IN PROGRESS |
| ISO 27001 | EU, UK, AU, SG, KR | HIGH | Q4 Year 1 | NOT STARTED |
| Cyber Essentials Plus | UK | HIGH | Q2 Year 1 | NOT STARTED |
| DSP Toolkit | UK (NHS) | HIGH | Q1 Year 1 | NOT STARTED |
| IRAP | AU (government) | MEDIUM | Q4 Year 1 | NOT STARTED |
| CSA STAR L1 | SG | MEDIUM | Q1 Year 1 | NOT STARTED |
| CSA STAR L2 | SG | LOW | Q2 Year 2 | NOT STARTED |
| CREST Pen Test | UK, EU, AU | HIGH | Q3 Year 1 | NOT STARTED |

---

## 4. Security Architecture Review — International Readiness

### 4.1 Zero Trust Architecture Status

| ZTA Principle | Implementation | Status |
|---------------|----------------|--------|
| Never trust, always verify | JWT authentication on every request; no implicit trust between services | ACTIVE |
| Least privilege | RBAC with minimal scope; IAM least-privilege roles | ACTIVE |
| Assume breach | Security event monitoring; SIEM; incident response plan | ACTIVE |
| Verify explicitly | MFA required for admin access; certificate-based service-to-service auth | ACTIVE |
| Micro-segmentation | VPC subnets per tier; security groups; NACLs | ACTIVE |

**ZTA posture is strong and consistent with international security expectations.**

### 4.2 Security Monitoring — International Extension

| Control | Current | International Addition |
|---------|---------|----------------------|
| SIEM | CloudWatch + alerts | Add GDPR-relevant event alerting (data access anomalies, cross-border data attempts) |
| Threat intelligence | AWS GuardDuty | Extend GuardDuty to all international regions |
| Security alerts | PagerDuty (US hours) | Follow-the-sun on-call coverage for international |
| Log retention | 90 days hot; 1 year archive | GDPR: retain audit logs per data retention policy; UK DSP: minimum 6 months |
| DLP | Not implemented | Evaluate AWS Macie for PHI/PII detection in S3 (international requirement) |

**Action:** Enable AWS GuardDuty and AWS Macie in all international regions at launch.

---

## 5. Security Controls Summary — International Requirements Gap Analysis

| Control Domain | Current Status | Gap | Action Required |
|----------------|---------------|-----|-----------------|
| Encryption (at rest/in transit) | ACTIVE | None | None |
| Key Management (per-tenant CMK) | ACTIVE | Regional key hierarchy | Activate per region at launch |
| Tenant Isolation (RLS + API) | ACTIVE | Regional routing enforcement | Deploy middleware per region |
| Data Sovereignty | PLANNED | Regional activation | Terraform IaC per region |
| ISO 27001 | NOT CERTIFIED | Full gap | Initiate Q1 Year 1 |
| SOC 2 Type II | IN PROGRESS | Completion | Target Q3 Year 1 |
| Cyber Essentials Plus | NOT CERTIFIED | Full gap | Initiate Q2 Year 1 |
| IRAP | NOT ASSESSED | Full gap | Initiate Q3 Year 1 |
| CSA STAR | NOT REGISTERED | Self-assessment | Q1 Year 1 (Level 1) |
| CREST Pen Test | Not performed | International scope needed | Engage Q2 Year 1 |
| Vulnerability Mgmt SLA | Informal | Formalize SLA tracking | Q1 Year 1 |
| International IR / Breach Notification | US only | International runbook | Q2 Year 1 |
| GuardDuty (international regions) | US only | Extend to all regions | At each regional launch |
| Macie (PHI detection) | Not deployed | Deploy per region | Q1 Year 1 |
| DAST (OWASP ZAP) | Not implemented | Integrate in CI/CD | Q2 Year 1 |

---

## 6. Document Metadata

| Field | Value |
|-------|-------|
| Author | LumenAI Security & Compliance Team |
| Review Date | Quarterly |
| Next Review | 2026-09-21 |
| Approvers | Chief Security Officer, Chief Compliance Officer, CTO |
| Related Documents | LUM-GLOBAL-003 (Privacy), LUM-GLOBAL-005 (Architecture), LUM-SEC series |
