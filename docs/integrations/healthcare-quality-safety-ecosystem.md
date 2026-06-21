# Healthcare Quality & Safety Ecosystem Integration Architecture

## Overview

LumenAI acts as an integration broker (hub-and-spoke model) between external healthcare quality and safety systems and the LumenAI instrument intelligence platform. External systems connect via standardized connector adapters; LumenAI normalizes, stores, and correlates the imported data without retaining unnecessary PHI.

---

## Integration Categories

### 1. SPD Tracking Systems
Sterile Processing Department systems tracking instrument lifecycle.

| System | Vendor | Data Types |
|--------|--------|------------|
| CensiTrac | Censis Technologies | Instrument checkout/checkin, tray tracking, sterilization cycles |
| SPM | Surgical Process Management | Instrument tracking, sterilization cycle records |
| ReadySet | ReadySet Surgical | Surgical readiness, loaner instrument tracking |
| Abacus | Abacus Surgical | Instrument management, repair history |
| VendorMade | VendorMade | Vendor loaner instruments, repair responses, baseline catalogs |

**Data flow:** External SPD system → Connector pull/webhook → Normalize to InstrumentTrackingRecord / TrayTrackingRecord / SterilizationCycleRecord / RepairHistoryRecord → Correlation engine → PatientImpactCorrelationCandidate

### 2. Quality & Safety Event Systems
Incident reporting and quality management systems.

| System | Vendor | Data Types |
|--------|--------|------------|
| SafeCare | SafeCare Technologies | Adverse events, near misses, good catches |
| RLDatix | RLDatix | Incidents, near misses, CAPAs, complaints |
| MIDAS | Conduent Health | Quality events, sentinel events, RCA records |
| Verge Health | Verge Health | Event reports, vendor concerns |

**Data flow:** External quality system → Connector pull → De-identify at source → Normalize to QualitySafetyEventRecord (de_identified=True enforced) → Correlation engine

### 3. Infection Prevention Systems
HAI surveillance and infection prevention platforms.

| System | Vendor | Data Types |
|--------|--------|------------|
| ICNet | BD (Becton Dickinson) | HAI surveillance, outbreak signals, infection flags |
| VigiLanz | VigiLanz | HAI alerts, SSI surveillance, pathogen signals |
| Theradoc | Premier | Infection prevention alerts, pharmacy surveillance |

**Data flow:** External IP system → Connector pull → De-identify at source → Normalize to InfectionPreventionEventRecord (de_identified=True enforced) → Correlation engine

### 4. Vendor & Manufacturer Systems
Loaner, repair, and catalog integrations with instrument manufacturers and repair vendors.

**Data types:** Loaner instrument manifests, repair orders, service bulletins, baseline instrument catalogs.

### 5. EHR / Clinical Data Systems
Procedure-level (non-patient-identified) data for instrument-to-procedure linking.

**Data types:** Procedure type, service line, OR location — no patient identifiers.

---

## Connector Types

| Type | Description | Use Cases |
|------|-------------|-----------|
| `api_pull` | LumenAI polls external REST API on schedule | CensiTrac, ICNet |
| `webhook` | External system pushes events to LumenAI endpoint | SafeCare, RLDatix |
| `csv` | Scheduled or manual CSV file ingestion | Legacy systems |
| `sftp` | SFTP file drop ingestion | On-premise systems |
| `manual` | Operator-uploaded file import | Ad-hoc data loads |

---

## Privacy Model

### Minimum Necessary Data Principle
LumenAI imports only the fields required to identify potential associations between instrument events and quality/safety signals. Fields imported:

- **SPD:** Instrument ID, UDI, barcode, tray ID, event type, timestamp, sterilization status, vendor ID
- **Quality/Safety:** Event type, severity, instrument reference, tray reference, CAPA ID — NO patient identifiers
- **Infection Prevention:** Event type, pathogen (de-identified), procedure type, service line, instrument reference — NO patient identifiers

### PHI Avoidance
The following fields are NEVER stored in any LumenAI integration model:
- `patient_id`, `mrn`, `medical_record_number`
- `dob`, `date_of_birth`
- `patient_name`, `first_name`, `last_name`
- `ssn`, `social_security_number`
- `address`, `phone`, `email`

All quality safety and infection prevention records have `de_identified = True` enforced at the application layer regardless of source system flag.

---

## Authentication Model

Each connector supports the following authentication types (type is stored; credentials are NOT stored in the database):

| Auth Type | Description | Credential Storage |
|-----------|-------------|-------------------|
| `oauth2` | OAuth 2.0 client credentials | Environment variable / secret manager |
| `api_key` | Static API key | Environment variable / secret manager |
| `basic` | HTTP Basic auth | Environment variable / secret manager |
| `saml` | SAML 2.0 SSO | Identity provider configuration |

The `auth_type` field in `ExternalSystemConnection` records only the type. No secrets, tokens, passwords, or credentials are stored in the database or `config_json`.

---

## Audit Trail Requirements

Every integration action creates an audit log entry:

| Action | Audit Event Type |
|--------|-----------------|
| List system connections | `integrations.systems.list` |
| Create system connection | `integrations.systems.create` |
| Test connection | `integrations.systems.test` |
| Preview import | `integrations.systems.preview_import` |
| Run import | `integrations.systems.run_import` |
| List import runs | `integrations.imports.list` |
| Import external events | `integrations.external_events.import` |
| Run correlation engine | `integrations.correlation.run` |
| View dashboard | `integrations.dashboard.view` |

Each audit entry records: tenant_id, actor_email, action_type, resource_type, resource_id, timestamp, and relevant details.

---

## Correlation Disclaimer

All correlation outputs include the following disclaimer:

> "Correlation candidates represent potential associations identified for human quality review. They do not establish causation."

All `PatientImpactCorrelationCandidate` records have `human_review_required = True`. Language in `association_reason` fields uses approved non-causal phrasing:
- "potential association"
- "possible contributing factor"
- "quality review recommended"
- "investigation candidate"
- "near-miss signal"
