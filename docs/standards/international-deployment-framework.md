# International Deployment Framework

**Version:** 1.0
**Status:** Published
**Maintained by:** GSIN Privacy Working Group & Legal Advisory Council

---

## Purpose

This framework governs the international expansion of the Global Surgical Intelligence Network, defining regional deployment models, privacy compliance requirements, data residency constraints, and cross-border data transfer rules for each supported geography.

**Disclaimer:** This framework is a governance and planning document. It does not constitute legal advice. All regional deployments must be reviewed by qualified legal and compliance professionals in the relevant jurisdiction. Human review required before any deployment decisions.

---

## 1. Regional Deployment Model

### Deployment Tiers

| Tier | Status | Description |
|------|--------|-------------|
| Active | Live operations | Full participant enrollment, data contribution, benchmark access |
| Pilot | Limited operations | Restricted participant count; governance and compliance validation ongoing |
| Planning | Pre-deployment | Regulatory assessment; no participant data collected |
| Suspended | Paused | Participant activity halted pending compliance resolution |

### Current Regional Status

| Region | Status | Participants | Privacy Framework | Data Residency |
|--------|--------|-------------|-------------------|----------------|
| North America | Active | 34 | HIPAA | United States |
| Europe | Active | 18 | GDPR | Germany (Frankfurt) |
| APAC | Pilot | 7 | PDPA (Singapore) | Singapore |
| Australia | Active | 11 | Privacy Act 1988 | Australia |
| LATAM | Planning | 0 | LGPD (Brazil) | TBD |
| MENA | Planning | 0 | Under assessment | TBD |

---

## 2. Privacy Framework by Region

### North America — HIPAA

**Applicability:** All participants handling Protected Health Information (PHI).

| Control | Requirement |
|---------|-------------|
| BAA | Business Associate Agreement required before data contribution |
| Minimum Necessary | Instrument quality data only; no patient identifiers |
| Encryption | AES-256 at rest; TLS 1.3 in transit |
| Audit Logging | All access events logged with compliance_flag |
| Breach Notification | 60-day notification requirement per HIPAA §164.412 |

**GSIN Implementation:** HIPAA BAA signed at enrollment. `hipaa_baa_signed_at` verified before any BAA-required system connections are permitted.

---

### Europe — GDPR

**Applicability:** All participants established in the European Economic Area (EEA).

| Control | Requirement |
|---------|-------------|
| Lawful Basis | Legitimate interest (instrument quality safety) + explicit consent |
| Data Minimization | Instrument-level aggregates only; no individual patient data |
| Data Residency | EU personal data must remain within EEA |
| Cross-Border Transfer | Standard Contractual Clauses (SCCs) required for EEA → non-EEA transfer |
| DPA | Data Processing Agreement required |
| Right to Erasure | Participant may request data withdrawal; 30-day SLA |
| DPO | Data Protection Officer registered with relevant supervisory authority |

**GSIN Implementation:** EU data hosted in Frankfurt (AWS eu-central-1). SCCs executed for any cross-border transfer. DPA signed at enrollment.

---

### APAC — PDPA (Singapore)

**Applicability:** Participants in Singapore; additional local laws apply per country.

| Control | Requirement |
|---------|-------------|
| Consent | Explicit consent for collection and use |
| Purpose Limitation | Data used only for stated quality intelligence purposes |
| Data Residency | Participant data stored in Singapore (AWS ap-southeast-1) |
| Transfer Limitation | Cross-border transfers require comparable protection level |
| Access | Participants may access and correct their contributed data |

**Regional Considerations:**
- Japan: APPI (Act on Protection of Personal Information) — PMDA alignment in progress
- China: PIPL (Personal Information Protection Law) — separate assessment required

---

### Australia — Privacy Act 1988

**Applicability:** All participants operating in Australia.

| Control | Requirement |
|---------|-------------|
| Australian Privacy Principles (APPs) | Full compliance required |
| Data Residency | Australian participant data stored in Australia (AWS ap-southeast-2) |
| Notifiable Data Breaches | NDB scheme compliance — notify OAIC within 30 days |
| Cross-Border Transfer | APP 8 compliance for any overseas disclosure |
| TGA Alignment | Post-market surveillance data aligned with TGA MDO 2021 |

---

### LATAM — LGPD (Brazil, Planning)

**Applicability:** Future participants in Brazil and broader LATAM region.

| Control | Requirement (Target) |
|---------|---------------------|
| Lawful Basis | Legitimate interest or explicit consent |
| Data Residency | Brazilian participant data stored in Brazil |
| ANPD Compliance | Notifications per Lei 13.709/2018 |
| DPO | Required for processing at scale |

**Status:** LGPD legal assessment in progress. Target launch: H2 2026.

---

## 3. Data Residency Framework

### Principles

1. **Default residency:** Participant data is stored in the region where the participant is enrolled
2. **No silent transfer:** Cross-border data movement requires explicit legal basis and participant notification
3. **Aggregation boundary:** Anonymized aggregate signals may cross borders only when k-anonymity ≥10 and DPA allows
4. **Audit trail:** Every cross-border data transfer is audit-logged

### Data Classification

| Data Type | Classification | Residency Requirement |
|-----------|---------------|-----------------------|
| Raw facility metrics (pre-aggregation) | Confidential | Must remain in participant's region |
| Anonymized aggregate signals (k≥10) | Network-shareable | May cross borders per DPA |
| Published benchmark data | Public (anonymized) | No residency restriction |
| Audit logs | Compliance | Must remain in participant's region for minimum retention period |
| Standards documents | Public | No residency restriction |

---

## 4. Compliance Mapping

### Regulatory Framework Alignment

| Regulation | Region | Key Instrument Quality Obligations | GSIN Coverage |
|-----------|--------|-------------------------------------|---------------|
| FDA 21 CFR 820 / QMSR | USA | Quality system records, complaint handling | Audit trails, CAPA tracking |
| EU MDR 2017/745 | EU | Post-market surveillance, vigilance reporting | Recall early warning, benchmark reports |
| TGA MDO 2021 | Australia | Post-market surveillance | Benchmark and recall signal data |
| ISO 13485 | Global | Quality management system | Baseline governance, CAPA workflows |
| AAMI ST79 | USA/Global | Instrument decontamination | Contamination classification standard |
| ISO 17664 | Global | Reprocessing of medical devices | Contamination classification standard |

---

## 5. Cross-Border Data Transfer Controls

### Transfer Authorization Matrix

| From | To | Authorization Required |
|------|----|-----------------------|
| North America | EU | SCC + DPA |
| EU | North America | SCC + DPA + GDPR adequacy assessment |
| APAC | North America | DPA + PDPA transfer impact assessment |
| Australia | Any | APP 8 compliance + DPA |
| Any | Any (aggregates only, k≥10) | DPA reference sufficient |

### Transfer Prohibition

The following data categories may **never** cross regional boundaries regardless of authorization:
- Individual patient identifiers
- Individual facility identifiers (raw)
- PHI of any kind
- Unaggregated instrument-level inspection records

---

## 6. International Readiness Assessment

### Readiness Checklist (per region)

- [ ] Privacy framework legal review completed
- [ ] Data residency infrastructure provisioned and verified
- [ ] DPA template localized and reviewed
- [ ] BAA/equivalent agreement template ready
- [ ] Cross-border transfer authorization documented
- [ ] Data breach notification process localized
- [ ] DPO or equivalent appointed (where required)
- [ ] Participant enrollment workflow validated
- [ ] Regulatory body notification filed (where required)
- [ ] Pilot participant agreement signed

---

*This document is for governance and planning purposes only. It does not constitute legal advice. All regional deployments require review by qualified legal and compliance professionals in the relevant jurisdiction. Human review required before deployment decisions.*
