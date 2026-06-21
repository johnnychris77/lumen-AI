# Privacy & Data Residency — LumenAI International

**Document ID:** LUM-GLOBAL-003  
**Version:** 1.0  
**Status:** Planning  
**Milestone:** P20 — International Expansion & Global Regulatory Readiness  
**Classification:** Compliance Confidential  

> **Framing Note:** This document describes LumenAI's privacy compliance planning posture. It does not constitute legal advice and should be reviewed by qualified privacy counsel in each applicable jurisdiction. Compliance posture descriptions reflect planned and in-progress capabilities.

---

## 1. Overview

LumenAI processes Protected Health Information (PHI) and other sensitive personal data in the context of SPD quality management and surgical instrument inspection. As LumenAI expands internationally, the platform must comply with diverse privacy frameworks governing health data handling, data residency, cross-border transfers, consent, audit logging, breach notification, retention, and deletion.

This document covers:
- Privacy framework requirements per jurisdiction
- LumenAI's current and planned compliance posture
- Multi-region data architecture for global data residency compliance

---

## 2. Privacy Framework Matrix

### 2.1 HIPAA (United States) — Reference Baseline

**Applicable Jurisdiction:** United States  
**Governing Law:** Health Insurance Portability and Accountability Act (1996), HITECH Act (2009), HIPAA Privacy Rule (45 CFR Part 164), Security Rule (45 CFR Part 164.300–318), Breach Notification Rule  

**Key Requirements for LumenAI**
- Business Associate Agreement (BAA): Required between LumenAI and all covered entity customers; executed before PHI access
- PHI handling: Minimum necessary principle; PHI used only for authorized purposes (SPD quality management, instrument tracking)
- Audit logging: Comprehensive audit logs of all PHI access, modification, disclosure
- Encryption: PHI encrypted at rest (AES-256) and in transit (TLS 1.2+) — addressable safeguard; LumenAI implements as required
- Access controls: Role-based access control (RBAC); unique user identification; automatic logoff
- Workforce training: Annual HIPAA training for workforce with PHI access

**Data Residency Requirements**
- HIPAA does not mandate US data residency; however, BAAs must ensure adequate protections
- LumenAI policy: US tenant data hosted in AWS us-east-1 (primary) + us-west-2 (DR)
- Cross-border: PHI must not transit to non-BAA-covered regions

**Cross-Border Transfer Controls**
- PHI must only be transferred to entities with valid BAAs in place
- Cloud subprocessors: AWS BAA in place; all AWS regions used must be covered

**Retention and Deletion**
- HIPAA: PHI retained per covered entity policies (minimum 6 years for certain records)
- LumenAI: Configurable retention per tenant; deletion on customer request with audit record
- Right to access: Patients may request PHI access through covered entity (not directly from LumenAI as BA)

**LumenAI Current Compliance Posture**
- Status: ACTIVE — BAA template executed; HIPAA controls implemented per P0–P19 milestones
- Audit logging: Implemented (structured logging, immutable audit trail)
- Encryption: AES-256 at rest, TLS 1.2+ in transit — ACTIVE
- BAA: Standard BAA template reviewed by counsel — ACTIVE
- Gaps: Workforce training program documentation, periodic access review automation

---

### 2.2 GDPR (European Union / EEA)

**Applicable Jurisdiction:** EU-27 Member States + EEA (Norway, Iceland, Liechtenstein)  
**Governing Law:** Regulation (EU) 2016/679 — General Data Protection Regulation; national implementing legislation per member state  

**Key Requirements for LumenAI**
- Legal basis for processing: Health data is special category (Article 9); requires explicit consent OR processing necessary for healthcare provision (Article 9(2)(h)) — healthcare institutions typically hold this basis; LumenAI as data processor supports data controllers (hospitals)
- Data Processing Agreement (DPA): Required between LumenAI (data processor) and each EU customer (data controller) — Article 28 DPA mandatory
- Data Subject Rights: Right of access, rectification, erasure, restriction, portability, objection — must be supported through data controller (hospital) workflow
- Data Protection by Design and Default: Privacy-by-design architecture required (Article 25)
- DPO: Data Protection Officer required if processing large-scale special category data; LumenAI should assess DPO requirement or appoint on voluntary basis
- Data Protection Impact Assessment (DPIA): Required for high-risk processing; AI-based processing of health data likely requires DPIA
- Breach notification: 72 hours to supervisory authority from processor notification to controller; controller notifies authority; processor must notify controller without undue delay
- Records of processing activities (Article 30): Mandatory records of all processing activities

**Data Residency Requirements**
- GDPR does not explicitly mandate EU data residency; however, Chapter V restricts transfers to third countries
- LumenAI policy: EU tenant data hosted in AWS eu-west-1 (Ireland) primary; eu-central-1 (Frankfurt) DR
- No cross-region replication of personal data outside EEA without adequate transfer mechanism
- Schrems II implications: Personal data transferred to US requires SCCs (Standard Contractual Clauses) or adequacy decision

**Cross-Border Transfer Controls**
- EU-US Data Privacy Framework (DPF): US companies certified under DPF may receive EU personal data without SCCs — LumenAI should pursue DPF certification
- SCCs: EU Standard Contractual Clauses (2021 version) as fallback for non-DPF transfers
- AWS: AWS EU regions are EEA-based; AWS participates in DPF; AWS DPA in place
- Transfer Impact Assessment (TIA): Required for transfers to non-adequate countries; document residual risks

**Retention and Deletion**
- Storage limitation: Data retained only as long as necessary for the purpose (Article 5(1)(e))
- LumenAI: Per-tenant configurable retention; automated deletion workflows; Right to Erasure (Article 17) workflow via data controller
- Pseudonymization: Instrument and inspection data pseudonymized where possible; patient identifiers minimized in SPD context

**LumenAI Current Compliance Posture**
- Status: PLANNING — EU infrastructure activation required
- DPA template: IN PREPARATION
- DPIA: IN PLANNING
- EU data residency: AWS eu-west-1 activation planned (LUM-GLOBAL-005 architecture)
- DPF certification: IN PLANNING
- DPO appointment: Under assessment
- Gaps: DPA execution, DPIA completion, Article 30 records, DPF certification, EU region activation

---

### 2.3 UK GDPR (United Kingdom)

**Applicable Jurisdiction:** United Kingdom (England, Scotland, Wales, Northern Ireland)  
**Governing Law:** UK GDPR (retained EU law post-Brexit, as amended by Data Protection, Privacy and Electronic Communications Regulations 2019); Data Protection Act 2018  

**Key Requirements for LumenAI**
- Substantially mirrors EU GDPR requirements; UK ICO (Information Commissioner's Office) is supervisory authority
- UK DPA required (equivalent to EU DPA Article 28)
- UK-specific: Caldicott Principles (health data-specific confidentiality framework in NHS context); National Data Guardian standards
- NHS Data Security and Protection (DSP) Toolkit: Annual self-assessment required for organizations processing NHS patient data
- DCB0129 Clinical Risk Management: Manufacturer clinical risk management standard for NHS deployments

**Data Residency Requirements**
- UK GDPR restricts transfers outside UK to adequate countries or with transfer mechanisms
- UK has adopted adequacy decisions for EU/EEA, some other countries
- US: UK-US data bridge (extension of EU-US DPF for UK) — LumenAI participation planned
- LumenAI policy: UK tenant data hosted in AWS eu-west-2 (London)

**Cross-Border Transfer Controls**
- UK IDTA (International Data Transfer Agreement): UK equivalent of SCCs for transfers to non-adequate countries
- UK-US Data Bridge: UK equivalent of EU-US DPF for US-based processors
- LumenAI: UK-US Data Bridge participation; IDTA as fallback

**Breach Notification**
- 72 hours to ICO from controller becoming aware (Article 33 UK GDPR)
- High risk breaches: Notification to data subjects without undue delay

**Retention and Deletion**
- Consistent with EU GDPR; NHS Records Management Code of Practice provides specific guidance for health records

**LumenAI Current Compliance Posture**
- Status: PLANNING
- UK DSP Toolkit: Registration in planning
- UK DPA template: IN PREPARATION
- UK data residency: AWS eu-west-2 (London) activation planned
- UK-US Data Bridge: Participation planned
- Gaps: DSP Toolkit registration, DCB0129 clinical risk management file, UK DPA execution, UKRP appointment

---

### 2.4 PIPEDA (Canada)

**Applicable Jurisdiction:** Canada — federal; Quebec Law 25 (Bill 64) as provincial supplement  
**Governing Law:** Personal Information Protection and Electronic Documents Act (PIPEDA); provincial equivalents (PIPA Alberta, PIPA BC, Quebec Law 25/Bill 64)  

**Key Requirements for LumenAI**
- Consent: PIPEDA requires knowledge and consent for collection, use, disclosure; health data requires express consent in most cases (hospitals obtain consent from patients; LumenAI as service provider)
- Privacy Notice: Clear notice to individuals about data collection/use
- CASL: Canada's Anti-Spam Legislation — not directly applicable to SPD workflow data
- Quebec Law 25 (in force Sept 2023): Stricter requirements — Privacy Impact Assessments (PIAs) for new technology systems; mandatory privacy officer appointment; right to data portability; breach notification to Commission d'accès à l'information (CAI) "as soon as reasonably possible" and to affected individuals if serious risk of injury
- Alberta PIPA: Breach notification to Privacy Commissioner if real risk of significant harm

**Data Residency Requirements**
- PIPEDA does not mandate Canadian data residency; accountability principle allows cross-border transfers with contractual protections
- Practical reality: Many provincial health authorities (Ontario, BC, Alberta) have policies requiring health data to remain in Canada
- LumenAI policy: Canadian tenant data hosted in AWS ca-central-1 (Montreal)
- Quebec: Additional consideration for Quebec tenant data; some Quebec health entities prefer Quebec-based hosting

**Cross-Border Transfer Controls**
- PIPEDA: Cross-border transfers allowed with contractual protections ensuring equivalent protection
- Data Processing Agreements with Canadian customers must address cross-border transfer restrictions
- Quebec Law 25: More stringent — cross-border transfers require PIA; must ensure equivalent protection in destination jurisdiction

**Breach Notification**
- PIPEDA: Breach notification to OPC (Office of the Privacy Commissioner) and affected individuals if "real risk of significant harm"
- Quebec Law 25: "As soon as reasonably possible" to CAI; 60 days maximum suggested guideline
- Alberta PIPA: "Without unreasonable delay"

**Retention and Deletion**
- PIPEDA: Retain only as long as necessary for identified purposes; destroy/anonymize when no longer needed
- LumenAI: Configurable retention; deletion on request

**LumenAI Current Compliance Posture**
- Status: PLANNING
- AWS ca-central-1: Activation planned
- PIA (Quebec Law 25): In planning
- Privacy officer: US-based team to extend coverage; Canadian privacy officer consideration for Quebec market
- Gaps: Canadian DPA template, Quebec PIA, ca-central-1 activation, breach notification procedures for each province

---

### 2.5 Australian Privacy Act 1988

**Applicable Jurisdiction:** Australia (Commonwealth); state/territory health privacy laws supplement  
**Governing Law:** Privacy Act 1988 (Cth); Australian Privacy Principles (APPs 1–13); Notifiable Data Breaches scheme (NDB, 2018); state equivalents (Health Records Act 2001 VIC, Health Records and Information Privacy Act 2002 NSW)  

**Key Requirements for LumenAI**
- Australian Privacy Principles: 13 APPs govern collection, use, disclosure, security, access, correction
- Health information: Sensitive information under Privacy Act; higher protections; generally requires consent or authorized purpose
- NDB Scheme: Mandatory breach notification to OAIC (Office of the Australian Information Commissioner) and affected individuals if "likely to result in serious harm" (assessed by entity)
- APP 11.1: Reasonable steps to protect personal information from misuse, interference, loss, unauthorized access/modification/disclosure
- APP 1: Open and transparent management of personal information

**Data Residency Requirements**
- Privacy Act APP 8: Cross-border disclosure requires reasonable steps to ensure recipient complies with APPs, OR is in a country with comparable protection; entity remains accountable for overseas-held data
- LumenAI policy: Australian tenant data hosted in AWS ap-southeast-2 (Sydney)
- No cross-region replication of Australian health data outside Australia without APP 8 compliance

**Cross-Border Transfer Controls**
- APP 8: Contractual protections required for cross-border transfers; or use of countries on approved list
- AWS: AWS Australia region in Sydney; AWS contractual terms cover APP 8 requirements
- LumenAI sub-processor agreements must extend APP 8 protections

**Breach Notification**
- NDB: Notify OAIC and individuals "as soon as practicable" — practical expectation 30 days from becoming aware (OAIC guidance)
- Assessment: Entity must assess whether eligible data breach within 30 days of suspicion

**Retention and Deletion**
- APP 11.2: Destroy or de-identify personal information when no longer needed for any purpose (including secondary/archival)
- State health records legislation may impose minimum retention periods (7 years minimum for adult health records in most states)

**LumenAI Current Compliance Posture**
- Status: PLANNING
- AWS ap-southeast-2: Activation planned
- NDB breach notification procedure: In planning
- APP 8 cross-border framework: In planning
- Gaps: Australian DPA/Privacy Agreement template, APP 8 sub-processor chain documentation, OAIC breach notification registration/procedure

---

### 2.6 PDPA (Singapore)

**Applicable Jurisdiction:** Singapore  
**Governing Law:** Personal Data Protection Act 2012 (No. 26 of 2012) as amended by PDPA Amendment Act 2020 (effective Feb 2021)  

**Key Requirements for LumenAI**
- Consent obligation: Collect, use, disclose personal data with consent; deemed consent and legitimate interests exceptions available
- Health data: Not separately classified as "sensitive" under PDPA but contractual and regulatory protections apply in healthcare context
- Purpose limitation: Personal data used only for notified purposes
- Data Protection Officer (DPO): Mandatory appointment of DPO for Singapore entities; LumenAI Singapore operations require DPO
- Mandatory breach notification: 3 calendar days to PDPC (Personal Data Protection Commission) for significant breaches; 30 calendar days for non-significant; notify affected individuals for "significant harm" breaches
- Data portability: Portability obligation under PDPA 2020 amendments (full effect TBD)

**Data Residency Requirements**
- PDPA: No mandatory data residency; cross-border transfer controls apply
- LumenAI policy: Singapore tenant data hosted in AWS ap-southeast-1 (Singapore)

**Cross-Border Transfer Controls**
- PDPA Section 26: Cross-border transfers require recipient to provide comparable protection; binding corporate rules, contractual clauses, or adequacy (binding standard)
- Singapore PDPC: Advisory guidelines on cross-border data transfers
- Standard Contractual Clauses: PDPC-approved SCCs or equivalent contractual protections

**Retention and Deletion**
- Retention limitation: Cease retention when purpose served; no longer than necessary
- LumenAI: Configurable retention; deletion workflows

**LumenAI Current Compliance Posture**
- Status: PLANNING
- DPO appointment (Singapore entity): Planned when Singapore entity established
- PDPA DPA template: In preparation
- AWS ap-southeast-1: Planned activation
- Breach notification (3-day PDPC): Procedure in planning — urgent given strict timeline

---

### 2.7 APPI (Japan)

**Applicable Jurisdiction:** Japan  
**Governing Law:** Act on the Protection of Personal Information (APPI), amended 2022 (fully effective April 2022); Ministerial Ordinance; Guidelines on Medical Information (MHLW)  

**Key Requirements for LumenAI**
- Personal information handling: Requires purpose specification; utilization within specified purpose; prohibition on third-party provision without consent
- Health/medical data: "Sensitive personal information" (yōhairyō kojin jōhō) — requires opt-in consent for collection; includes "medical records, medical history, disability"
- PPC registration: Personal Information Protection Commission (PPC) oversight
- Cross-border transfer: Explicit consent required OR recipient country deemed adequate OR recipient business operator established equivalent standards (binding corporate rules equivalent)
- Breach notification: Mandatory notification to PPC and data subjects since 2022 (within "promptly" — practical 30-day guideline for reporting to PPC)

**Data Residency Requirements**
- APPI: No explicit data residency mandate; cross-border transfer consent/adequacy required
- LumenAI policy: Japan tenant data hosted in AWS ap-northeast-1 (Tokyo) when Japan market entered

**Cross-Border Transfer Controls**
- APPI: EU/UK adequacy; some other countries; US not yet deemed adequate; requires explicit consent or binding standard
- AWS: AWS Japan region; AWS contractual standards can support APPI cross-border requirements
- LumenAI: Japan-to-US data transfers (e.g., for global support teams) require explicit consent or binding standards

**Breach Notification**
- 2022 amendment: Mandatory PPC notification and data subject notification; report to PPC "without undue delay" and within 30 days from discovery (60 days for unauthorized external access)

**LumenAI Current Compliance Posture**
- Status: NOT STARTED (Tier 3 market)
- AWS ap-northeast-1: Planned for Japan market entry
- APPI DPA: Not yet developed
- Japanese DPO: Required when Japan entity/operations established

---

### 2.8 PIPA (South Korea)

**Applicable Jurisdiction:** Republic of Korea  
**Governing Law:** Personal Information Protection Act (PIPA, Act No. 10465, 2011, amended 2023); PIPA Enforcement Decree; Act on Promotion of Information and Communications Network Utilization and Information Protection  

**Key Requirements for LumenAI**
- PIPC (Personal Information Protection Commission): Primary oversight body
- Sensitive information: Health/medical data is "sensitive information" requiring separate explicit consent
- Privacy policy: Public privacy policy required; annual update
- Security measures: Mandatory technical and administrative security measures per PISC regulations
- Cross-border transfer: Requires data subject consent OR contractual/regulatory equivalent protection
- PIPA 2023 Amendment: Aligned more closely with GDPR; enhanced data subject rights; mandatory DPO for large processors

**Data Residency Requirements**
- PIPA: No mandatory Korea data residency; cross-border transfer restrictions apply
- LumenAI policy: Korean tenant data in AWS ap-northeast-2 (Seoul) when Korea market entered

**Cross-Border Transfer Controls**
- PIPA: Explicit consent; or contractual protections; or PIPC-approved BCR/SCCs
- AWS Seoul region: Supports Korean data hosting; AWS contractual protections available

**Breach Notification**
- PIPA Article 34: Notify data subjects and PIPC "without delay" from discovery; within 72 hours per 2023 amendment guidance

**LumenAI Current Compliance Posture**
- Status: PLANNING (Tier 2 market)
- AWS ap-northeast-2 (Seoul): Planned
- Korean DPA template: Not yet developed
- Korean-language privacy policy: Required on market entry

---

### 2.9 UAE PDPL

**Applicable Jurisdiction:** United Arab Emirates (Federal); DIFC (Dubai International Financial Centre) has separate DIFC DP Law 2020; ADGM (Abu Dhabi Global Market) has separate framework  
**Governing Law:** Federal Decree-Law No. 45 of 2021 on Personal Data Protection (PDPL); effective from March 2022 with implementation period  

**Key Requirements for LumenAI**
- Personal data processing: Requires legal basis; consent or contractual necessity
- Health data: Sensitive data requiring explicit consent
- Data Controller obligations: Appoint data protection officer; maintain records of processing; notify breaches
- Healthcare data: UAE Ministry of Health regulations (MoHAP) govern health data separately; DHA (Dubai Health Authority) data regulations for Dubai health data
- PDPL enforcement: UAE Data Office (under TRA — Telecommunications and Digital Government Regulatory Authority)

**Data Residency Requirements**
- PDPL: Cross-border transfer restrictions; requires UAE Data Office approval or adequate protection equivalent
- Healthcare-specific: DHA and DOH may have additional residency requirements for patient data
- LumenAI policy: UAE tenant data in AWS me-south-1 (Bahrain) — closest AWS Middle East region; UAE-specific region (AWS me-central-1 announced but limited services) — assess availability at market entry

**Cross-Border Transfer Controls**
- PDPL: Cross-border transfer to countries with comparable protection or with UAE Data Office approval
- SCCs or equivalent: UAE contractual protections framework in development

**Breach Notification**
- PDPL: Notify UAE Data Office and data subjects within 72 hours of becoming aware of a breach that may cause harm

**LumenAI Current Compliance Posture**
- Status: NOT STARTED (Tier 3 market)
- Monitoring: PDPL implementation guidance evolution

---

### 2.10 Saudi Arabia PDPL

**Applicable Jurisdiction:** Kingdom of Saudi Arabia  
**Governing Law:** Personal Data Protection Law (PDPL, Royal Decree M/19, 2021); implementing regulations issued 2023; effective September 2023 with grace period  

**Key Requirements for LumenAI**
- SDAIA: Saudi Data and AI Authority — oversight body
- Sensitive data: Health data is sensitive; requires explicit consent and additional protections
- Data Controller: Must be registered; Privacy Notice required in Arabic
- Healthcare data: NCA (National Cybersecurity Authority) Essential Cybersecurity Controls apply to health sector entities
- Data localization: PDPL generally prohibits transfer of personal data outside KSA without SDAIA approval or agreement ensuring equivalent protection; healthcare data localization may be required

**Data Residency Requirements**
- Strong localization preference: Saudi PDPL and sector-specific guidance strongly favor in-country hosting
- LumenAI policy: Saudi Arabia market entry requires AWS me-south-1 (Bahrain) at minimum; AWS me-central-1 (UAE) as alternative; fully in-country hosting preferred
- Healthcare sector: MOH may require data to remain in Saudi Arabia; assess at market entry

**Cross-Border Transfer Controls**
- PDPL: Transfer only with SDAIA approval; or where transfer is necessary for contract performance; or recipient provides equivalent protection
- Health sector: Additional MOH transfer restrictions anticipated

**Breach Notification**
- PDPL: Notify SDAIA and data subjects within 72 hours of discovery

**LumenAI Current Compliance Posture**
- Status: NOT STARTED (Tier 3 market)
- Arabic PDPL privacy policy: Required on market entry

---

## 3. Multi-Region Data Architecture

### 3.1 Architecture Principles

1. **Data Sovereignty First**: PHI and personal data of each region's customers are processed and stored exclusively within that region's designated AWS infrastructure
2. **No Cross-Region PHI Replication**: Personal data never replicates across regional boundaries; operational/telemetry data (non-PHI) may be aggregated centrally with de-identification
3. **Tenant-Region Binding**: Each tenant's `tenant_region` configuration is immutable post-onboarding; enforced at API Gateway and application layer
4. **Regional Key Management**: Each region maintains independent AWS KMS key hierarchy; keys never exported cross-region
5. **Audit Trail Integrity**: Regional audit logs are immutable; cross-region log aggregation for non-PHI operational metrics only

### 3.2 Regional Infrastructure Map

```
┌─────────────────────────────────────────────────────────┐
│                 GLOBAL CONTROL PLANE                     │
│         (Non-PHI: Metadata, Routing, Auth tokens)        │
│              AWS us-east-1 (primary)                     │
│         CloudFront CDN (static assets only)              │
└──────────────────────┬──────────────────────────────────┘
                       │ (routing only, no PHI)
       ┌───────────────┼──────────────────────┐
       │               │                      │
┌──────▼──────┐ ┌──────▼──────┐ ┌────────────▼────────────┐
│ NORTH AM    │ │ EUROPE      │ │ ASIA PACIFIC            │
│ us-east-1   │ │ eu-west-1   │ │ ap-southeast-1          │
│ us-west-2DR │ │ eu-central-1│ │ ap-northeast-1          │
│             │ │ eu-west-2   │ │ ap-southeast-2          │
│ HIPAA       │ │ GDPR/UKGDPR │ │ PDPA/APPI/AppPriv       │
│ PIPEDA      │ │             │ │                          │
└─────────────┘ └─────────────┘ └─────────────────────────┘
```

### 3.3 Data Residency Enforcement

**Tenant Region Configuration**

```json
{
  "tenant_id": "hosp-12345",
  "tenant_region": "eu-west-1",
  "data_residency": "EU",
  "privacy_framework": ["GDPR"],
  "cross_border_transfers_permitted": false,
  "kms_key_arn": "arn:aws:kms:eu-west-1:...",
  "s3_bucket": "lumenai-eu-west-1-data-hosp12345",
  "rds_endpoint": "lumenai-eu-west-1.cluster.rds.amazonaws.com"
}
```

**API Gateway Enforcement**

- Incoming requests checked against `tenant_region` in JWT token claims
- Requests from EU tenants routed exclusively to EU regional endpoints
- Cross-region data requests rejected with 403 (data sovereignty violation) and audited

### 3.4 Regional Data Services

| Region | Primary | DR | S3 Bucket Policy | RDS Configuration | KMS |
|--------|---------|----|--------------------|-------------------|-----|
| North America | us-east-1 | us-west-2 | us-east-1 primary; no cross-region for PHI | Multi-AZ us-east-1; read replica us-west-2 (no PHI sync for HIPAA) | us-east-1 KMS |
| Europe (EU) | eu-west-1 | eu-central-1 | EU only; no cross-border replication | Multi-AZ eu-west-1; eu-central-1 backup (within EEA) | eu-west-1 KMS |
| United Kingdom | eu-west-2 | eu-west-1* | UK only | Multi-AZ eu-west-2 | eu-west-2 KMS |
| Canada | ca-central-1 | ca-west-1 | Canada only | Multi-AZ ca-central-1 | ca-central-1 KMS |
| Singapore | ap-southeast-1 | ap-southeast-1 (AZ-2) | Singapore only | Multi-AZ ap-southeast-1 | ap-southeast-1 KMS |
| Australia | ap-southeast-2 | ap-southeast-2 (AZ-2) | Australia only | Multi-AZ ap-southeast-2 | ap-southeast-2 KMS |
| Japan | ap-northeast-1 | ap-northeast-3 | Japan only | Multi-AZ ap-northeast-1 | ap-northeast-1 KMS |

*Note: UK to EU-West-1 DR requires post-Brexit adequacy assessment; UK-Ireland adequacy exists; confirm at implementation.

### 3.5 Non-PHI Cross-Region Data Flows (Permitted)

- Product telemetry (de-identified performance metrics): Aggregated to us-east-1
- ML model weights and inference updates: Deployed per-region from central model registry (no patient data in model artifacts)
- Security event logs (de-identified): SIEM aggregation for global security monitoring
- Billing/commercial data: us-east-1 (non-PHI)

---

## 4. Privacy Compliance Summary Dashboard

| Framework | Jurisdiction | Breach Notification | Data Residency Policy | LumenAI Status |
|-----------|-------------|--------------------|-----------------------|----------------|
| HIPAA | US | No fixed timeline (without undue delay) | US regions | ACTIVE |
| GDPR | EU/EEA | 72 hours (to SA) | EU regions | PLANNING |
| UK GDPR | UK | 72 hours (to ICO) | eu-west-2 | PLANNING |
| PIPEDA | Canada | Variable per province | ca-central-1 | PLANNING |
| Quebec Law 25 | Quebec | ASAP / 60 days | ca-central-1 | PLANNING |
| Australian Privacy Act | Australia | ASAP / 30 days | ap-southeast-2 | PLANNING |
| PDPA | Singapore | 3 days (significant) / 30 days | ap-southeast-1 | PLANNING |
| APPI | Japan | 30 days | ap-northeast-1 | NOT STARTED |
| PIPA | South Korea | 72 hours | ap-northeast-2 | PLANNING |
| UAE PDPL | UAE | 72 hours | me-south-1 | NOT STARTED |
| Saudi PDPL | Saudi Arabia | 72 hours | me-south-1 / in-country | NOT STARTED |

---

## 5. Document Metadata

| Field | Value |
|-------|-------|
| Author | LumenAI Privacy & Compliance Team |
| Review Date | Quarterly |
| Next Review | 2026-09-21 |
| Approvers | Chief Privacy Officer, Chief Legal Officer, CTO |
| Related Documents | LUM-GLOBAL-005 (Multi-Region Architecture) |
