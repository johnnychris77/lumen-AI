# Regulatory Readiness Matrix — LumenAI International

**Document ID:** LUM-GLOBAL-002  
**Version:** 1.0  
**Status:** Planning  
**Milestone:** P20 — International Expansion & Global Regulatory Readiness  
**Classification:** Regulatory Confidential  

> **Framing Note:** This document uses planning/readiness language throughout. LumenAI has not received regulatory clearance, registration, or authorization in any jurisdiction other than as reflected in current FDA submission status. All timelines are estimates; actual regulatory authority review times are not guaranteed. The term "clearance/registration" is used consistent with each jurisdiction's terminology — no "approval" for marketing is claimed.

---

## 1. Overview

LumenAI Module A (Computer Vision-based surgical instrument inspection and defect detection) is classified as Software as a Medical Device (SaMD) under IMDRF definitions. This matrix documents the regulatory classification, evidence requirements, cybersecurity expectations, documentation requirements, estimated authorization timelines, and current readiness status for each target regulatory jurisdiction.

**Device Description for Regulatory Purposes:**
- Intended use: AI/ML-based quality analysis of sterilized surgical instruments in SPD/CSSD settings; outputs inspection quality scores and flags instruments for human review
- Key qualifier: All outputs include `human_review_required: true`; the system supports, not replaces, human inspection decisions
- IEC 62304 Software Lifecycle classification: Class B (standalone SaMD without direct patient contact)
- IMDRF SaMD Risk Category: Category II (serious situation + non-critical decision support) — does not drive or inform critical/emergency decisions

---

## 2. Regulatory Body Matrix

### 2.1 FDA (United States) — Reference Baseline

| Parameter | Detail |
|-----------|--------|
| **Regulatory Body** | U.S. Food and Drug Administration — Center for Devices and Radiological Health (CDRH) |
| **Classification Assumption** | Class II — 21 CFR Part 880 (General Hospital and Personal Use Devices); SaMD classification per CDRH Digital Health Policy |
| **Pathway** | 510(k) Premarket Notification (most likely); De Novo if no predicate identified |
| **Authorization Term** | 510(k) Clearance |

**Evidence Requirements**
- Performance testing: Sensitivity/specificity data for defect detection; comparison to predicate device or reference standard
- Clinical/analytical study: Usability study (human factors) per FDA HFE guidance; performance data from pilot sites
- Software documentation: Software Bill of Materials (SBOM), Design History File (DHF), IEC 62304 lifecycle documentation
- Risk management: ISO 14971 risk management file
- Cybersecurity: FDA Cybersecurity in Medical Devices guidance (September 2023); SBOM required; vulnerability management plan; 5-year support lifecycle documentation

**Documentation Requirements**
- 510(k) summary or substantial equivalence documentation
- Device description and intended use
- Performance testing data
- Software documentation per FDA software guidance
- Cybersecurity documentation per 2023 FDA guidance
- Labeling (Instructions for Use)

**Estimated Timeline**
- Standard 510(k) review: 90-day FDA target (actual average ~160 days historically for digital health)
- Total from submission preparation to clearance: 12–18 months (including preparation time)

**Current Readiness Status**
- Status: SUBMISSION IN PREPARATION (P19 milestones completed)
- QMS: ISO 13485-aligned; MDSAP audit in planning
- Software documentation: DHF in progress per LUM-REG-series documents
- Cybersecurity: LUM-SEC series completed; SBOM in preparation
- Gaps: Human factors validation study (in planning per LUM-HF-001); final performance data collection

---

### 2.2 Health Canada — MDL/MDALL

| Parameter | Detail |
|-----------|--------|
| **Regulatory Body** | Health Canada — Medical Devices Directorate (MDD) |
| **Classification Assumption** | Class II Medical Device under Medical Devices Regulations (SOR/98-282); SaMD classification based on IMDRF framework adopted by Health Canada |
| **Pathway** | Medical Device Licence (MDL) application |
| **Authorization Term** | Medical Device Licence |

**Evidence Requirements**
- Safety and effectiveness: Performance data demonstrating device functions as intended; evidence of risk/benefit profile
- Standards compliance: IEC 62304, ISO 14971, ISO 13485
- Reference to FDA clearance: With FDA 510(k) clearance, Health Canada MDL Class II pathway is significantly expedited — HC allows attestation of substantial equivalence to cleared US device
- MDSAP: QMS audit under MDSAP covers Health Canada requirements; MDSAP certificate significantly streamlines evidence package

**Cybersecurity Expectations**
- Health Canada cybersecurity guidance for medical devices (2019) and updates
- IMDRF cybersecurity principles (IMDRF/CYBER WG/N60FINAL:2020) adopted by Health Canada
- Software vulnerability management plan required
- Incident response for cybersecurity events

**Documentation Requirements**
- MDL application form (MDL Form HC 3011)
- Device description, intended use, indications
- Standards attestation (ISO 13485, IEC 62304, ISO 14971)
- Summary of performance and safety data
- Labeling (English and French for national market)
- MDSAP certificate (if held)

**Estimated Timeline**
- Class II target review: 15 business days after submission accepted as complete (Health Canada target)
- With FDA clearance reference: 3–6 months total preparation + review
- Without FDA clearance: 6–12 months
- Planning estimate: 6–12 months to MDL from current state

**Current Readiness Status**
- Status: PLANNING — not yet initiated
- Advantage: High documentation reuse from FDA submission package
- Gaps: French labeling, Canadian-specific intended use language, MDSAP audit completion
- Readiness Score: 60% (documentation foundation exists; Canada-specific preparation needed)

---

### 2.3 EU MDR (European Union)

| Parameter | Detail |
|-----------|--------|
| **Regulatory Body** | EU MDR (Regulation (EU) 2017/745); Notified Body required for Class IIa+ |
| **Classification Assumption** | Class IIa under Rule 11 (software intended to provide information used for diagnostic or therapeutic purposes); potentially Class IIb if claims extend to clinical decision support influencing patient management |
| **Pathway** | Notified Body conformity assessment; CE marking |
| **Authorization Term** | CE Marking (CE Certificate issued by Notified Body) |

**Evidence Requirements**
- Clinical Evaluation Report (CER): Per MEDDEV 2.7/1 Rev. 4; systematic literature review + clinical data; PMCF (Post-Market Clinical Follow-up) plan
- Performance data: Analytical/clinical performance studies; comparison to state of the art
- PMS (Post-Market Surveillance) system: EU MDR Article 83–86; PSUR (Periodic Safety Update Report) for Class IIa+
- Technical Documentation: Per Annex II and III of EU MDR; substantially more extensive than FDA 510(k)
- EUDAMED registration: Mandatory — economic operator and device registration in EU database
- UDI: Unique Device Identification required; EUDAMED UDI-DI registration

**Cybersecurity Expectations**
- MDCG 2019-16: Guidance on cybersecurity for medical devices
- MDCG 2020-1: Guidance on clinical evaluation of SaMD
- ENISA guidelines: European Union Agency for Cybersecurity guidance
- IEC 81001-5-1 (Health software — security activities in the product lifecycle)
- SBOM increasingly expected by NB assessors

**Documentation Requirements**
- Technical Documentation (Annex II EU MDR): Device description, design and manufacturing information, general safety and performance requirements (GSPR) checklist, benefit-risk analysis, product verification and validation
- Technical Documentation on Post-Market Surveillance (Annex III): PMS plan, PSUR, PMCF plan
- Declaration of Conformity
- QMS: ISO 13485 certification from EU-recognized accreditation body (mandatory for NB assessment)
- Authorized Representative (EU AR) in an EU member state required for non-EU manufacturers

**Estimated Timeline**
- NB engagement: 3–6 months to NB agreement (NB capacity constraints are significant — delays common)
- NB assessment: 12–18 months after document submission acceptance
- Total from preparation start to CE Certificate: 18–30 months
- Planning estimate: 24 months from full engagement

**Current Readiness Status**
- Status: EARLY PLANNING
- Gaps: EU-specific CER, PMCF plan, EUDAMED registration, EU Authorized Representative appointment, NB selection and engagement, GSPR checklist completion
- Readiness Score: 30% (foundational QMS and documentation exist; EU MDR-specific package requires significant investment)

---

### 2.4 UK MDR / UKCA (United Kingdom)

| Parameter | Detail |
|-----------|--------|
| **Regulatory Body** | MHRA (Medicines and Healthcare products Regulatory Agency) |
| **Classification Assumption** | Class IIa under UK MDR 2002 (as amended); consistent with EU MDR classification logic |
| **Pathway** | UKCA marking via UK Approved Body; or CE marking recognition during transitional period (subject to MHRA transition timeline updates) |
| **Authorization Term** | UKCA Registration (or CE Mark recognition during transition) |

**Evidence Requirements**
- UK MDR 2002 conformity assessment: UK-specific technical file requirements
- DTAC compliance: Digital Technology Assessment Criteria for Health and Social Care (NHS England DTAC) — required for NHS procurement; covers clinical safety (DCB0129/0160), data security (DSP Toolkit), interoperability, usability
- Clinical safety: DCB0129 (Clinical Risk Management for Manufacturers) and DCB0160 (Clinical Risk Management for Deployments) — NHS-specific clinical risk management standards
- Performance evidence consistent with EU MDR requirements

**Cybersecurity Expectations**
- MHRA Guidance: "Cybersecurity for medical devices and clinical engineering" updated guidance
- NCSC (National Cyber Security Centre): Cyber Essentials / Cyber Essentials Plus certification strongly recommended for NHS market
- DSP Toolkit: NHS Data Security and Protection Toolkit compliance required for NHS deployments
- DTAC cybersecurity domain assessment

**Documentation Requirements**
- Technical File per UK MDR 2002
- UK Declaration of Conformity
- UKCA marking (or CE marking during transitional period)
- UK Responsible Person (UKRP) appointment required for non-UK manufacturers
- Labeling: UK-specific (UKCA marking, UKRP address)
- DTAC documentation pack for NHS procurement

**Estimated Timeline**
- UK Approved Body assessment: 12–18 months (similar NB capacity challenges to EU)
- DTAC assessment: 3–6 months (can run in parallel)
- DSP Toolkit: Annual; can register and begin immediately
- Planning estimate: 12–18 months to UKCA registration

**Current Readiness Status**
- Status: PLANNING
- Advantage: UK MDR closely mirrors EU MDR; technical documentation reuse high
- Gaps: UK Approved Body selection, UKRP appointment, DTAC preparation, DSP Toolkit registration, DCB0129 clinical risk management file
- Readiness Score: 40%

---

### 2.5 TGA (Australia)

| Parameter | Detail |
|-----------|--------|
| **Regulatory Body** | TGA — Therapeutic Goods Administration (Department of Health and Aged Care) |
| **Classification Assumption** | Class IIb medical device (SaMD under TGA framework; TGA SaMD guidance document 2022); higher than EU IIa due to TGA classification rules for software |
| **Pathway** | ARTG (Australian Register of Therapeutic Goods) inclusion via Conformity Assessment Body or TGA assessment |
| **Authorization Term** | ARTG Inclusion |

**Evidence Requirements**
- Evidence of conformity: TGA-accepted conformity assessment (ISO 13485 QMS + IEC 62304 + ISO 14971)
- MDSAP: TGA participates in MDSAP — MDSAP QMS audit significantly streamlines TGA conformity assessment; single audit covers FDA, HC, TGA, ANVISA, PMDA
- Performance data: Summary of safety and performance; clinical evidence consistent with intended use
- TGA SaMD guidance: "Regulation of software as a medical device" (TGA, 2022) — compliance checklist

**Cybersecurity Expectations**
- TGA does not have separate cybersecurity guidance; references IEC 62443, IMDRF cybersecurity principles
- IRAP (Information Security Registered Assessors Program): Required for Australian Government health data hosting; relevant if targeting public hospital sector with government data
- ASD Essential Eight: Australian Signals Directorate controls baseline for Australian government systems

**Documentation Requirements**
- ARTG application with device description and intended use
- Evidence of conformity (MDSAP certificate or TGA conformity assessment)
- Summary of Safety and Performance
- Australian Sponsor required (Australian entity or registered business)
- Labeling with ARTG number post-inclusion
- Unique Device Identifier (UDI) registration increasingly required

**Estimated Timeline**
- With MDSAP certificate: 6–12 months to ARTG inclusion
- Without MDSAP certificate: 12–18 months
- Planning estimate: 12 months from MDSAP audit completion

**Current Readiness Status**
- Status: PLANNING (dependent on MDSAP audit)
- Advantage: MDSAP leverage; English documentation; high overlap with FDA package
- Gaps: Australian Sponsor appointment, ARTG application, MDSAP audit completion, Australian-specific labeling
- Readiness Score: 50%

---

### 2.6 HSA (Singapore)

| Parameter | Detail |
|-----------|--------|
| **Regulatory Body** | HSA — Health Sciences Authority |
| **Classification Assumption** | Class B or Class C (HSA 4-class system: A, B, C, D); SaMD with significant risk of harm if malfunctioning but supporting human decision → likely Class B; may be Class C if classified as providing diagnosis/treatment information |
| **Pathway** | Product Registration via MEDICS (Medical Device Information and Communication System) |
| **Authorization Term** | HSA Product Registration |

**Evidence Requirements**
- Conformity: ISO 13485 QMS certificate from SAC-accredited or IMDRF-recognized body
- Performance data: Evidence of safety and effectiveness; HSA accepts FDA clearance or CE marking as reference evidence (ASEAN AMDD framework)
- ASEAN AMDD: Singapore is a signatory to ASEAN Medical Device Directive harmonization; AMDD alignment facilitates regional expansion

**Cybersecurity Expectations**
- HSA cybersecurity guidance references IMDRF principles
- CSA (Cyber Security Agency of Singapore) standards: CSA Cybersecurity Labelling Scheme (CLS) for IoT/connected devices — relevant for cloud-hosted SaaS
- MAS TRM (Monetary Authority of Singapore Technology Risk Management) — if financial data involved (not primary concern)

**Documentation Requirements**
- MEDICS registration application
- ISO 13485 certificate
- Performance summary / safety data
- Labeling (English)
- Technical documentation summary
- FDA clearance or CE marking supporting document (if held)

**Estimated Timeline**
- Class B: 60-day target review (HSA) with complete submission
- Class C: ~150 days
- Total preparation + review: 6–12 months

**Current Readiness Status**
- Status: PLANNING
- Advantage: English regulatory environment; FDA reference accepted; relatively streamlined pathway
- Gaps: MEDICS registration preparation, Singapore-specific labeling, ISO 13485 SAC-recognized certificate
- Readiness Score: 55%

---

### 2.7 PMDA (Japan)

| Parameter | Detail |
|-----------|--------|
| **Regulatory Body** | PMDA (Pharmaceuticals and Medical Devices Agency) / MHLW (Ministry of Health, Labour and Welfare) |
| **Classification Assumption** | Class II (kanri iryo kiki) — "controlled medical device"; SaMD classification under MHLW AI/ML guidance (2021); AI-specific guidelines from MHLW and PMDA |
| **Pathway** | Ninsho (certification via Registered Certification Body — RCB) for Class II; or Nintei (designation) for novel devices |
| **Authorization Term** | Marketing Certification (Ninsho) or Ministry Approval (Nintei) |

**Evidence Requirements**
- Japan-specific standards: QMS Ordinance (equivalent to ISO 13485 but Japan-specific); requires Japan-domestic QMS registration
- JNLM (Japan-specific performance standards)
- AI/ML SaMD: MHLW/PMDA guidance on AI-based medical devices (2021, 2023 updates); change management for AI learning systems
- MDSAP: PMDA participates — MDSAP audit recognized but Japan-specific QMS Ordinance registration still required

**Cybersecurity Expectations**
- MHLW cybersecurity guidance for medical devices (2019, updated 2022)
- NISC (National center of Incident readiness and Strategy for Cybersecurity) guidelines
- PMDA actively reviews cybersecurity documentation in technical assessments

**Documentation Requirements**
- All documentation in JAPANESE (mandatory)
- QMS Ordinance compliance documentation
- Technical specification documents (Japanese format)
- DMAH (Designated Marketing Authorization Holder) appointment — required for foreign manufacturers; Japanese entity must hold the marketing authorization
- Clinical evidence in Japanese health system context preferred

**Estimated Timeline**
- RCB certification (Class II): 12–18 months after complete Japanese-language submission
- Total from localization + preparation + review: 24–36 months
- Planning estimate: 30 months

**Current Readiness Status**
- Status: NOT STARTED
- Major Gaps: Japanese language documentation, DMAH identification and agreement, Japanese QMS Ordinance registration, Japanese-format technical files
- Readiness Score: 15%

---

### 2.8 MFDS (South Korea)

| Parameter | Detail |
|-----------|--------|
| **Regulatory Body** | MFDS — Ministry of Food and Drug Safety |
| **Classification Assumption** | Class II or Class III (Korea 4-class system); SaMD under MFDS Notice 2019-38 on SaMD software classification; AI-based detection likely Class II |
| **Pathway** | MFDS Medical Device Registration |
| **Authorization Term** | MFDS Product Registration |

**Evidence Requirements**
- ISO 13485 QMS certificate (internationally recognized body)
- Performance data: Clinical/analytical performance study; Korean-specific evidence may be requested
- IEC 62304 software lifecycle documentation
- Safety data per ISO 14971

**Cybersecurity Expectations**
- MFDS Guidance on cybersecurity for medical devices (2022)
- References IMDRF cybersecurity principles
- Software change management documentation required for AI/ML

**Documentation Requirements**
- MFDS registration application
- Korean Regulatory Affairs Handler (Korean entity or agent required)
- Technical documentation (English acceptable; Korean translation of key sections)
- ISO 13485 and IEC 62304 compliance evidence
- Korean-specific labeling

**Estimated Timeline**
- Class II: ~9–12 months with complete submission
- Total preparation + review: 12–18 months

**Current Readiness Status**
- Status: PLANNING
- Gaps: Korean regulatory agent identification, Korean labeling, Korea-specific technical file adaptation
- Readiness Score: 35%

---

## 3. Regulatory Readiness Summary Dashboard

| Jurisdiction | Classification | Pathway | Est. Timeline | Readiness Score | Priority |
|-------------|----------------|---------|---------------|-----------------|----------|
| FDA (US) | Class II | 510(k) | 12–18 months | 70% | ACTIVE |
| Health Canada | Class II | MDL | 6–12 months | 60% | TIER 1 |
| UK MDR/UKCA | Class IIa | UKCA / UK AB | 12–18 months | 40% | TIER 1 |
| TGA Australia | Class IIb | ARTG | 12 months (post-MDSAP) | 50% | TIER 1 |
| HSA Singapore | Class B/C | MEDICS | 6–12 months | 55% | TIER 1 |
| EU MDR | Class IIa | CE Mark / NB | 18–30 months | 30% | TIER 2 |
| MFDS Korea | Class II | MFDS Reg. | 12–18 months | 35% | TIER 2 |
| PMDA Japan | Class II | Ninsho | 24–36 months | 15% | TIER 3 |

---

## 4. Cross-Cutting Regulatory Themes

### 4.1 MDSAP — Multi-Market Leverage Strategy

MDSAP (Medical Device Single Audit Program) participation covers: FDA, Health Canada, TGA, ANVISA (Brazil), PMDA (Japan). A single annual MDSAP audit satisfies QMS audit requirements for five regulatory authorities simultaneously. Pursuing MDSAP certification is the highest-leverage regulatory investment for LumenAI international expansion.

**MDSAP Program Members:** FDA, Health Canada, TGA, ANVISA, PMDA  
**Action:** Engage MDSAP-authorized Auditing Organization (e.g., BSI, SGS, TÜV SÜD) for initial audit  
**Timeline:** MDSAP audit preparation: 3–6 months; initial audit: 1–2 days; certificate: 30–60 days post-audit

### 4.2 IMDRF Framework Adoption

IMDRF (International Medical Device Regulators Forum) principles are adopted by: Health Canada, TGA, HSA, MFDS, PMDA (partially). Documentation aligned with IMDRF SaMD N23 (Risk Categorization), IMDRF N41 (Software Change Management), IMDRF CYBER N60 (Cybersecurity) can be leveraged across multiple submissions.

### 4.3 AI/ML Regulatory Evolution

All major regulatory authorities (FDA, Health Canada, EU MDR, MHRA, TGA, PMDA, MFDS) are actively developing or updating AI/ML SaMD-specific guidance. Predetermined Change Control Plans (PCCP) — adopted by FDA — are being considered by other authorities. Maintaining a PCCP-compliant change management approach protects LumenAI across all markets.

### 4.4 Cybersecurity — Cross-Jurisdictional Requirements

All jurisdictions require cybersecurity documentation. SBOM is explicitly required by FDA; expected/recommended by EU MDR, MHRA, Health Canada. Maintaining a current SBOM and vulnerability management program satisfies all jurisdictions' expectations.

---

## 5. Document Metadata

| Field | Value |
|-------|-------|
| Author | LumenAI Regulatory Affairs Team |
| Review Date | Quarterly |
| Next Review | 2026-09-21 |
| Approvers | Chief Regulatory Officer, VP Quality |
| Related Documents | LUM-GLOBAL-001 (Market Strategy), LUM-REG series |
