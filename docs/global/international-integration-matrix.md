# International Integration Matrix — LumenAI Global

**Document ID:** LUM-GLOBAL-006  
**Version:** 1.0  
**Status:** Planning  
**Milestone:** P20 — International Expansion & Global Regulatory Readiness  
**Classification:** Product Confidential  

---

## 1. Overview

This document catalogs international equivalents of SPD tracking systems, quality management systems, patient safety platforms, infection prevention systems, and EHR systems relevant to LumenAI's international markets. For each system, it documents vendor information, primary markets, data formats, integration complexity, and LumenAI integration status.

**Integration Status Definitions:**
- **Live**: Integration complete and deployed in production
- **In Progress**: Integration development underway
- **Planned**: Integration on roadmap with timeline commitment
- **Under Evaluation**: System identified; integration scope under assessment
- **Not Planned**: Integration not currently on roadmap; can be revisited

---

## 2. SPD Tracking Systems

### 2.1 Censitrac

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Censitrac (BD — Becton, Dickinson and Company) |
| **Primary Markets** | Global (US, Canada, UK, Australia, Singapore, EU) |
| **Deployment Scope** | Enterprise hospitals worldwide; market leader in instrument tracking |
| **Data Format** | Proprietary REST API; HL7 2.x for certain integrations; CSV export for reporting |
| **Integration Type** | Bidirectional — LumenAI receives instrument/tray data from Censitrac; sends inspection outcomes back |
| **Key Integration Points** | Instrument catalog sync, tray assembly records, sterilization cycle data, inspection trigger/result |
| **Integration Complexity** | MEDIUM — REST API available; BD Partnership Program required for production access |
| **Authentication** | OAuth 2.0 / API key (varies by deployment version) |
| **LumenAI Integration Status** | IN PROGRESS (US primary deployment); extends to international deployments |
| **International Considerations** | Censitrac v6+ has multi-language support; same API across regions; country-specific configuration |

### 2.2 Censis Technologies (SPM — Surgical Process Manager)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Censis Technologies (acquired by Fortive/ASP) |
| **Primary Markets** | Global — US, Canada, UK, Australia, EU, Singapore |
| **Deployment Scope** | Mid-to-large hospitals; strong in US Southeast and growing internationally |
| **Data Format** | REST API (v2+); HL7 FHIR R4 partial support; HL7 2.x for legacy integrations |
| **Integration Type** | Bidirectional — instrument tracking, tray management, sterilization data |
| **Integration Complexity** | MEDIUM — documented API; Censis Integration Partner Program |
| **LumenAI Integration Status** | PLANNED (Year 1 international launch coincides with Censis global expansion) |
| **International Considerations** | Multi-currency, multi-language support in Censis 2024+ releases |

### 2.3 TelaTrac

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Telios (formerly TelaTrac) |
| **Primary Markets** | US primary; limited Canada/Australia presence |
| **Data Format** | HL7 2.x; proprietary API |
| **Integration Type** | Bidirectional — instrument tracking data exchange |
| **Integration Complexity** | MEDIUM |
| **LumenAI Integration Status** | IN PROGRESS (US); international expansion limited by TelaTrac's market presence |
| **International Considerations** | Not a priority for international markets where Censitrac/T-DOC dominate |

### 2.4 Getinge T-DOC

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Getinge AB |
| **Primary Markets** | Europe (dominant — Germany, Netherlands, Nordics, Belgium, France), UK, Australia, Singapore |
| **Deployment Scope** | Market leader in European hospital CSSD management; large enterprise deployments |
| **Data Format** | HL7 2.x (ORM/ORU messages); Getinge DataCenter REST API (v2+); DICOM for imaging (limited); CSV/XML export |
| **Integration Type** | Bidirectional — instrument catalog, tray records, sterilization cycle completion, decontamination workflow |
| **Key Integration Points** | T-DOC Instrument ID → LumenAI inspection trigger; LumenAI inspection pass/fail → T-DOC cycle completion record |
| **Integration Complexity** | HIGH — Getinge Integration Framework requires formal partnership; data model mapping complex (German terminology by default) |
| **Authentication** | Getinge Integration Hub (GIH) — proprietary secure messaging layer |
| **LumenAI Integration Status** | PLANNED — Priority integration for EU/UK/AU launch |
| **International Considerations** | T-DOC configurations vary significantly by country; German language data fields; UTF-8 required |
| **Partnership Required** | Getinge Technology Alliance Partner Program |

### 2.5 Belimed

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Belimed AG (Metall Zug Group) |
| **Primary Markets** | Europe (Switzerland, Germany, Austria, UK), Australia, Middle East |
| **Deployment Scope** | Equipment manufacturer with integrated tracking; wash/sterilize equipment with data capture |
| **Data Format** | OPC-UA (equipment integration), Belimed Connect REST API, HL7 2.x partial |
| **Integration Type** | Equipment data integration — sterilizer/washer cycle data, load records |
| **Integration Complexity** | HIGH — equipment-level integration; requires on-site middleware |
| **LumenAI Integration Status** | UNDER EVALUATION — sterilizer cycle data relevant for inspection correlation |
| **International Considerations** | German-language primary configuration; international deployments in EN |

### 2.6 Sterilucent

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Sterilucent Inc. |
| **Primary Markets** | Canada, US |
| **Data Format** | Proprietary; REST API emerging |
| **Integration Complexity** | MEDIUM |
| **LumenAI Integration Status** | PLANNED — Canada launch priority |
| **International Considerations** | Primary Canada market — important for Canadian launch; bilingual (EN/FR) Canadian deployments |

### 2.7 iSterile / Sorin (LivaNova)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | LivaNova PLC (formerly Sorin Group) |
| **Primary Markets** | Europe (Italy, France, Germany, Spain) |
| **Data Format** | Proprietary; HL7 2.x |
| **Integration Complexity** | HIGH — limited API documentation; requires partnership |
| **LumenAI Integration Status** | NOT PLANNED (Year 1–2) — lower priority given Getinge T-DOC dominance in EU |
| **International Considerations** | Italian/French primary; assess for Southern EU expansion |

---

## 3. Quality Management Systems

### 3.1 Q-Pulse (Ideagen)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Ideagen PLC |
| **Primary Markets** | UK (NHS — very widely deployed), EU, Australia, New Zealand, Canada |
| **Deployment Scope** | Dominant in NHS quality management; widely used in Australian health networks |
| **Data Format** | Q-Pulse REST API (Ideagen Cloud); legacy versions: XML/CSV export; SOAP in older deployments |
| **Integration Type** | Unidirectional (initially) — LumenAI quality events → Q-Pulse non-conformance records |
| **Key Integration Points** | Inspection failure events → Q-Pulse non-conformance; trend data → Q-Pulse audit evidence |
| **Integration Complexity** | MEDIUM — REST API available in Ideagen Cloud (SaaS version); on-premises legacy more complex |
| **LumenAI Integration Status** | PLANNED — UK/AU launch priority (high NHS market relevance) |
| **International Considerations** | Ideagen Cloud is globally deployed SaaS; API consistent; on-premise version API varies |

### 3.2 Enablon (Wolters Kluwer)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Wolters Kluwer (acquired Enablon) |
| **Primary Markets** | Global — EU, North America, APAC; large enterprise |
| **Data Format** | REST API; OData; integration via Enablon Open Platform |
| **Integration Type** | Quality event integration; CAPA management |
| **Integration Complexity** | HIGH — enterprise platform; significant configuration |
| **LumenAI Integration Status** | UNDER EVALUATION — large health system enterprise quality programs |
| **International Considerations** | Multi-language, multi-region cloud deployment |

### 3.3 Intelex (EHSQ Software)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Intelex Technologies (acquired by Fortive) |
| **Primary Markets** | Global — North America, EU, APAC |
| **Data Format** | REST API; webhook; Intelex Integration Hub |
| **Integration Complexity** | MEDIUM-HIGH |
| **LumenAI Integration Status** | UNDER EVALUATION |

### 3.4 EtQ Reliance (Hexagon)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Hexagon AB (acquired EtQ) |
| **Primary Markets** | Global — US, EU, APAC; manufacturing and healthcare |
| **Data Format** | REST API; EtQ Connect integration framework |
| **Integration Complexity** | MEDIUM |
| **LumenAI Integration Status** | UNDER EVALUATION — pharmaceutical/medical device QMS users |

---

## 4. Patient Safety Systems

### 4.1 DATIX (RLDatix)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | RLDatix (Riskonnect company) |
| **Primary Markets** | UK (NHS — dominant market leader), Australia, Ireland, Canada, global |
| **Deployment Scope** | NHS standard patient safety incident system; replacing Ulysses/Safeguard across NHS England |
| **Data Format** | DATIX API (REST); HL7 FHIR Patient Safety Module (emerging); CSV export |
| **Integration Type** | Bidirectional — LumenAI inspection failures → DATIX incident records; DATIX safety signals → LumenAI risk context |
| **Key Integration Points** | Instrument failure creating patient safety event → DATIX incident report trigger |
| **Integration Complexity** | MEDIUM — DATIX API access via NHS Digital API Management |
| **LumenAI Integration Status** | PLANNED — UK launch priority (NHS Safety Culture requirement) |
| **International Considerations** | DATIX global deployment (Australia, Canada) — same API; UK DSEQ (Digital Standards Ecosystem for Quality) alignment |

### 4.2 Riskman (RiskMan International)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | RiskMan International Pty Ltd |
| **Primary Markets** | Australia (dominant), New Zealand, parts of SE Asia |
| **Deployment Scope** | Widely deployed in Australian state health departments (Victoria, SA, WA, QLD) |
| **Data Format** | RiskMan REST API (v2+); XML import/export; CSV |
| **Integration Type** | Unidirectional initially — LumenAI quality events → Riskman incident/quality register |
| **Integration Complexity** | MEDIUM |
| **LumenAI Integration Status** | PLANNED — Australia launch priority |
| **International Considerations** | Australia/NZ only; leverage for AU and NZ launch |

### 4.3 Pascal (NHS England)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | NHS England (internal system being developed — Patient Safety Incident Response Framework tool) |
| **Primary Markets** | NHS England |
| **Data Format** | FHIR R4 (planned); NHS Digital API Management Gateway |
| **Integration Type** | Future integration — PSIR (Patient Safety Incident Response) reporting |
| **Integration Complexity** | HIGH (NHS internal system; access via NHS Digital partnership) |
| **LumenAI Integration Status** | UNDER EVALUATION — NHS England market; post-LEARN program rollout |

### 4.4 RL6 / RLDatix (Global)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | RLDatix (formerly RL Solutions) |
| **Primary Markets** | Global — Canada (dominant market), US, Australia, UK, Middle East |
| **Data Format** | RL API (REST); HL7 FHIR partial; CSV/XML |
| **Integration Type** | Quality event integration; incident reporting |
| **Integration Complexity** | MEDIUM |
| **LumenAI Integration Status** | PLANNED — Canada launch (RL6 dominant in Canadian health networks) |

---

## 5. Infection Prevention Systems

### 5.1 ICP.doc

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Informa Medical GmbH |
| **Primary Markets** | EU (Germany, Austria, Switzerland — DACH region), Netherlands |
| **Deployment Scope** | Infection control documentation; widely deployed in German hospital networks |
| **Data Format** | Proprietary; HL7 2.x for some integrations; XML export |
| **Integration Type** | Contextual — surgical site infection (SSI) data → correlation with LumenAI instrument inspection records |
| **Integration Complexity** | HIGH — German market-specific; limited public API |
| **LumenAI Integration Status** | UNDER EVALUATION — Germany market entry (infection prevention correlation use case) |
| **International Considerations** | German-language system; DACH focus |

### 5.2 Vigil-Inf

| Attribute | Detail |
|-----------|--------|
| **Vendor** | B. Braun Melsungen AG (Vigil-Inf platform) |
| **Primary Markets** | EU (Germany, France, Benelux) |
| **Data Format** | Proprietary; XML/CSV exchange |
| **Integration Complexity** | HIGH |
| **LumenAI Integration Status** | NOT PLANNED (Year 1–2) |

### 5.3 ICNET (Baxter International)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Baxter International (acquired Carefusion ICNET) |
| **Primary Markets** | Global — US, UK, EU, Australia, Canada |
| **Deployment Scope** | Infection surveillance and outbreak detection; deployed in NHS and large health systems globally |
| **Data Format** | HL7 2.x (ADT, ORM, ORU); REST API (newer versions); FHIR R4 adoption in progress |
| **Integration Type** | HAI (Healthcare Associated Infection) surveillance data — correlation with SPD quality events |
| **Key Integration Points** | SSI/HAI events → cross-reference with LumenAI inspection records for instrument-linked infection investigation |
| **Integration Complexity** | MEDIUM — HL7 standard interface; Baxter integration program |
| **LumenAI Integration Status** | PLANNED — UK/AU launch (infection prevention value proposition) |
| **International Considerations** | Global deployment; HL7 standard consistent; regional terminology differences handled |

---

## 6. EHR Systems

### 6.1 Epic

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Epic Systems Corporation |
| **Primary Markets** | Global — US (dominant), UK (growing), Canada, Singapore (NUHS), Australia (growing), Netherlands, UAE |
| **Data Format** | HL7 FHIR R4 (primary — Epic App Orchard); HL7 2.x (legacy); Epic API (proprietary) |
| **Integration Type** | SPD integration — case scheduling (OR procedure → instrument tray request → LumenAI inspection); patient visit correlation |
| **Key Integration Points** | OR scheduling → instrument demand planning; procedure completion → SPD workflow trigger |
| **Integration Complexity** | MEDIUM — Epic FHIR R4 well-documented; Epic App Orchard marketplace pathway available |
| **Authentication** | SMART on FHIR (OAuth 2.0 PKCE) |
| **LumenAI Integration Status** | IN PROGRESS — Epic App Orchard submission planned |
| **International Considerations** | Epic global deployments use same FHIR API; multi-language Epic supports localization; regional Epic instances |

### 6.2 Cerner / Oracle Health

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Oracle Health (formerly Cerner Corporation) |
| **Primary Markets** | Global — US, UK, Canada, Australia, UAE, Saudi Arabia (MOH national deployment) |
| **Data Format** | HL7 FHIR R4 (Cerner MillenniumIQ FHIR); HL7 2.x; CCD; Cerner Integration Engine |
| **Integration Type** | Same as Epic — OR scheduling, SPD workflow triggers |
| **Integration Complexity** | MEDIUM — FHIR R4 well-documented; Cerner Open Developer Experience (code.cerner.com) |
| **LumenAI Integration Status** | PLANNED — high priority for UK (Cerner NHS deployments), Saudi Arabia (MOH-Cerner) |
| **International Considerations** | Oracle Health global deployment; FHIR API consistent; Saudi MOH national Cerner deployment strategically important |

### 6.3 Meditech

| Attribute | Detail |
|-----------|--------|
| **Vendor** | MEDITECH |
| **Primary Markets** | US, Canada, UK, Australia, Ireland, New Zealand |
| **Data Format** | HL7 FHIR R4 (Meditech Expanse FHIR); HL7 2.x (legacy Magic/Client/Server) |
| **Integration Complexity** | MEDIUM — FHIR R4 in Expanse platform |
| **LumenAI Integration Status** | PLANNED — Canada/UK market relevance (Meditech community hospital deployments) |

### 6.4 TPP SystmOne

| Attribute | Detail |
|-----------|--------|
| **Vendor** | TPP (The Phoenix Partnership) |
| **Primary Markets** | UK (NHS Primary Care — very widely deployed in GP practices and community care) |
| **Data Format** | HL7 FHIR R4 (TPP FHIR API via NHS Digital); SystmOne proprietary XML |
| **Integration Type** | Limited relevance for SPD workflow; patient care context only |
| **Integration Complexity** | HIGH — NHS Digital API access required; TPP closed ecosystem |
| **LumenAI Integration Status** | NOT PLANNED — primary care system; limited SPD workflow relevance |

### 6.5 EMIS Health

| Attribute | Detail |
|-----------|--------|
| **Vendor** | EMIS Health (Formerly Egton Medical Information Systems) |
| **Primary Markets** | UK (NHS Primary Care and Community Care) |
| **Data Format** | HL7 FHIR R4 (EMIS API); proprietary |
| **Integration Type** | Limited relevance for acute SPD workflow |
| **LumenAI Integration Status** | NOT PLANNED — primary care focus |

### 6.6 Sunrise (Altera Digital Health / Harris Healthcare)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Altera Digital Health (formerly Allscripts Hospital & Large Physician Practice) |
| **Primary Markets** | EU (UK NHS acute deployments, Netherlands, UAE), US |
| **Data Format** | HL7 FHIR R4; HL7 2.x |
| **Integration Complexity** | MEDIUM |
| **LumenAI Integration Status** | UNDER EVALUATION — EU/UK acute hospital deployments |
| **International Considerations** | Sunrise Clinical Manager deployed in several NHS Trusts; Netherlands; SingHealth (some modules) |

### 6.7 MedWorxs

| Attribute | Detail |
|-----------|--------|
| **Vendor** | MedWorxs Pty Ltd |
| **Primary Markets** | Australia — widely deployed in public hospital Patient Administration Systems |
| **Data Format** | HL7 2.x (ADT, ORM); limited FHIR; proprietary API |
| **Integration Type** | Patient administrative data; OR scheduling for instrument demand |
| **Integration Complexity** | HIGH — Australian market-specific; limited API documentation publicly available |
| **LumenAI Integration Status** | PLANNED — Australia launch; critical for public hospital sector |
| **International Considerations** | Australia-specific; required for state health department hospitals (NSW, VIC, QLD deployments) |

### 6.8 Best Practice (Australia/NZ GP)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Best Practice Software |
| **Primary Markets** | Australia, New Zealand (GP and community health) |
| **Data Format** | HL7 2.x; proprietary API |
| **LumenAI Integration Status** | NOT PLANNED — primary care; limited acute SPD relevance |

### 6.9 iHIS (Integrated Health Information Systems)

| Attribute | Detail |
|-----------|--------|
| **Vendor** | Integrated Health Information Systems Pte Ltd (IHiS) — Singapore MOH Holdings subsidiary; now rebranded Synapxe |
| **Primary Markets** | Singapore (all public hospital clusters: SingHealth, NHG, NUHS) |
| **Data Format** | HL7 FHIR R4 (National Electronic Health Record — NEHR API); HL7 2.x; proprietary |
| **Integration Type** | Singapore public hospital EMR; OR scheduling, patient administration |
| **Integration Complexity** | HIGH — Singapore government healthcare platform; requires MOH Holdings partnership |
| **LumenAI Integration Status** | PLANNED — Singapore launch priority (iHIS/Synapxe powers all public Singapore hospitals) |
| **International Considerations** | Singapore-specific; Synapxe API gateway for connected health applications |

---

## 7. Integration Priority Matrix

| System | Regions | Business Value | Complexity | Priority | Target Quarter |
|--------|---------|----------------|------------|----------|----------------|
| Censitrac | Global | HIGH — market leader | MEDIUM | P1 | Q1 Year 1 (extends globally from US) |
| Getinge T-DOC | EU, UK, AU | HIGH — EU market leader | HIGH | P1 | Q2 Year 1 (EU/UK launch) |
| Epic (FHIR) | Global | HIGH — large hospital share | MEDIUM | P1 | Q1 Year 1 (App Orchard) |
| Cerner/Oracle (FHIR) | Global | HIGH — UK/Saudi/global | MEDIUM | P1 | Q1 Year 1 |
| RL6/RLDatix | Canada, AU | HIGH — patient safety | MEDIUM | P1 | Q2 Year 1 (CA/AU) |
| Riskman | Australia, NZ | HIGH — AU market standard | MEDIUM | P1 | Q2 Year 1 (AU) |
| DATIX | UK | HIGH — NHS standard | MEDIUM | P1 | Q2 Year 1 (UK) |
| Q-Pulse | UK, AU | HIGH — NHS QMS | MEDIUM | P1 | Q2 Year 1 (UK) |
| ICNET | UK, AU, Global | MEDIUM — infection prevention | MEDIUM | P2 | Q3 Year 1 |
| Sterilucent | Canada | MEDIUM — Canada-specific | MEDIUM | P2 | Q2 Year 1 (CA) |
| MedWorxs | Australia | MEDIUM — AU public hospitals | HIGH | P2 | Q3 Year 1 (AU) |
| iHIS/Synapxe | Singapore | MEDIUM — SG public sector | HIGH | P2 | Q3 Year 1 (SG) |
| Meditech | Canada, UK | MEDIUM — community hospitals | MEDIUM | P2 | Q3 Year 1 |
| Censis/SPM | Global | MEDIUM — growing global | MEDIUM | P2 | Q3 Year 1 |
| ICP.doc | Germany/EU | MEDIUM — infection correlation | HIGH | P3 | Q1 Year 2 (EU) |
| Enablon | Global | LOW-MEDIUM — enterprise QMS | HIGH | P3 | Year 2 |
| Belimed | EU, AU | LOW-MEDIUM — equipment data | HIGH | P3 | Year 2 |

---

## 8. Integration Architecture Patterns

### 8.1 HL7 FHIR R4 (Primary Pattern)

```
LumenAI API ←→ FHIR Adapter Layer ←→ Hospital FHIR Server
                │
                ├── ServiceRequest (instrument tray request)
                ├── Procedure (surgical case)
                ├── Device (surgical instrument — FHIR Device resource)
                └── Observation (inspection result as FHIR Observation)
```

### 8.2 HL7 v2.x Legacy Pattern

```
Hospital ADT/ORM → HL7 v2.x Message → LumenAI HL7 Receiver →
  → Parse ORM_O01 (Order) → Create LumenAI inspection job
  → LumenAI inspection complete → ORU_R01 (Result) → Hospital SPD system
```

### 8.3 REST API Pattern (SPD Systems)

```
LumenAI API ←→ Integration Middleware ←→ SPD System API
              (Regional deployment)
              - Authentication: OAuth 2.0 / API Key
              - Format: JSON REST
              - Encryption: TLS 1.2+
              - Retry: Exponential backoff (3 attempts)
              - DLQ: Failed messages → Dead Letter Queue → alert
```

---

## 9. Document Metadata

| Field | Value |
|-------|-------|
| Author | LumenAI Integrations Team |
| Review Date | Quarterly |
| Next Review | 2026-09-21 |
| Approvers | VP Engineering, VP Product, VP International Sales |
| Related Documents | LUM-GLOBAL-001 (Market Strategy), LUM-INT series (integration specs) |
