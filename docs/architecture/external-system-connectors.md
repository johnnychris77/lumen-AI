# External System Connectors — Architecture

> All connectors operate under the Patient Safety Intelligence Layer's association-not-causation principle. No patient identifiers are stored post-import. De-identification is mandatory before data enters the LumenAI database.

---

## SPD Tracking Systems

**Systems**: CensiTrac, SPM (Sterilization Process Manager), ReadySet, Abacus

### Purpose
Track instrument lifecycle: sterilization cycles, tray management, repair history, instrument location, and reprocessing compliance.

### Integration Method
- **CensiTrac**: REST API (JSON) — instrument tracking, tray assignment, cycle log
- **SPM**: CSV import / REST API — sterilization cycle records, parameter logs
- **ReadySet**: REST API — tray management, repair history
- **Abacus**: REST API / CSV import — instrument inventory, maintenance records

### Data Elements Received
- Instrument ID / UDI / barcode
- Sterilization cycle ID, date, parameters (temperature, pressure, time)
- Tray composition
- Repair history entries
- Reprocessing technician ID (de-identified to role)

### De-identification Requirements
- Technician identifiers must be replaced with role codes before import
- No patient scheduling information from tray assignment records

### Audit Requirements
- Each import batch creates an `ExternalEventImport` record per event
- `raw_payload_hash` (SHA-256) stored for integrity verification
- Connector sync logged to `ExternalSystemConnector.last_sync_at`

### Current Status
**Planned** — connector framework available; system-specific adapters in development

---

## Quality / Event Reporting Systems

**Systems**: SafeCare, RLDatix, MIDAS, Verge Health

### Purpose
Receive adverse event reports, near miss records, CAPA items, and incident data from facility event reporting platforms.

### Integration Method
- **SafeCare**: REST API (JSON) — adverse events, near miss, patient safety events
- **RLDatix**: REST API (JSON) + webhook — incident reports, CAPA workflow
- **MIDAS**: REST API (JSON) — occurrence reporting, quality metrics
- **Verge Health**: REST API (JSON) — compliance events, policy deviations

### Data Elements Received
- Event ID (source system)
- Event type: adverse_event, near_miss, capa, sse, near_miss
- Event date
- Instrument reference (UDI/barcode if documented)
- Event description (de-identified)
- CAPA ID (if applicable)

### De-identification Requirements
- **Mandatory**: All patient identifiers (name, MRN, DOB, SSN, encounter ID) must be stripped at the connector layer before creating `ExternalEventImport`
- Event descriptions containing identifiable information must be redacted
- `de_identified` flag must be `True` before import proceeds; events with `de_identified=False` are rejected

### Audit Requirements
- Every imported event creates an audit log entry with `action_type="patient_safety.events.import"`
- Source system documented in `connector_id` reference

### Current Status
**Available** — SafeCare and RLDatix connectors ready for configuration; MIDAS and Verge Health planned

---

## Infection Prevention Systems

**Systems**: ICNet, VigiLanz, Theradoc

### Purpose
Receive HAI (Healthcare-Associated Infection) surveillance data, SSI (Surgical Site Infection) tracking, outbreak detection signals, and infection control alerts.

### Integration Method
- **ICNet**: HL7 FHIR R4 — HAI surveillance, infection control records
- **VigiLanz**: REST API (JSON) — real-time HAI alerts, outbreak detection
- **Theradoc**: HL7 FHIR R4 / REST API — antimicrobial stewardship, SSI tracking

### Data Elements Received
- Signal type: hai_review_candidate, ssi_review_candidate, outbreak_signal
- Pathogen (organism name — no patient linkage)
- Procedure type category (e.g., "orthopedic", "cardiac")
- Event date
- Instrument type associated with procedure (if documented)

### De-identification Requirements
- Patient admission and discharge dates removed
- Unit/location generalised to facility-level only
- Pathogen and procedure type retained as quality markers

### Audit Requirements
- `InfectionPreventionSignal` created per imported signal
- All signals carry `human_review_required=True`
- Infection prevention team notification logged

### Current Status
**Planned** — VigiLanz integration prioritised for next development cycle

---

## Vendor / Manufacturer Systems

**Systems**: VendorMade

### Purpose
Receive vendor performance data, instrument procurement records, product quality notifications, and field safety notices.

### Integration Method
- **VendorMade**: REST API (JSON) — vendor scorecard, procurement records, field notices

### Data Elements Received
- Vendor ID
- Product / instrument type
- Quality scorecard metrics
- Field safety notice IDs
- Procurement volume and delivery performance

### De-identification Requirements
- No patient data in vendor feeds — de-identification not applicable at this layer
- Internal facility pricing data removed (commercial sensitivity)

### Audit Requirements
- Vendor data sync logged to `ExternalSystemConnector`
- Quality signals derived from vendor data tagged with `event_source="vendor"`

### Current Status
**Available** — integrated with Vendor Intelligence module (P7)

---

## Optional EHR Integration (Future)

**Systems**: Epic, Cerner

### Purpose
Provide de-identified procedure context to support instrument-procedure correlation. Enables matching of instrument reprocessing records to procedure categories (not individual patients).

### Integration Method
- **Epic**: HL7 FHIR R4 — de-identified procedure encounter data
- **Cerner**: HL7 FHIR R4 — de-identified procedure encounter data

### Data Elements Received (De-identified only)
- Procedure type category
- Procedure date (date only, no time)
- Instrument set / tray used (by tray ID, not patient)
- Facility and unit code

### De-identification Requirements
- **Strictly enforced**: No patient name, MRN, DOB, insurance ID, or any HIPAA-defined PHI
- Only aggregate and instrument-level linkage permitted
- Must comply with HIPAA Safe Harbor de-identification standard (45 CFR §164.514(b))

### Audit Requirements
- All FHIR queries logged with timestamp and requesting tenant
- De-identification verification flag required before data ingestion

### Current Status
**Future** — planned for a subsequent milestone; requires HIPAA BAA and security review

---

## Connector Framework

All connectors are managed via the `ExternalSystemConnector` model:

```
ExternalSystemConnector
  tenant_id        — tenant scope
  system_name      — "safecare", "rldatix", etc.
  system_category  — "quality_event", "infection_prevention", etc.
  connection_status — configured / active / error / disabled
  last_sync_at     — last successful data pull
  events_imported  — running count
  config_json      — non-sensitive config (endpoint URL, not credentials)
```

Credentials are **never** stored in `config_json` or any database field. They are retrieved from the environment or secrets manager at runtime.
