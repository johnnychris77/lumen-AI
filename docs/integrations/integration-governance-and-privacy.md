# Integration Governance & Privacy Policy

## 1. Tenant Isolation Policy

All integration data is strictly scoped to the originating tenant:

- Every model includes a non-nullable, indexed `tenant_id` column
- All queries filter by `tenant_id` derived from the authenticated request context
- No cross-tenant queries are permitted at any layer
- Audit logs are scoped per tenant
- A tenant may never access another tenant's system connections, import runs, event records, or correlation candidates

Violations of tenant isolation are a critical security defect and must be escalated immediately.

---

## 2. Role-Based Access Control (RBAC)

| Action | Required Role |
|--------|--------------|
| View system connections | `quality_analyst`, `quality_manager`, `admin` |
| Create/modify system connections | `integration_admin`, `admin` |
| Test connection | `integration_admin`, `admin` |
| Run preview import | `integration_admin`, `quality_manager`, `admin` |
| Run full import | `integration_admin`, `admin` |
| View import runs | `quality_analyst`, `quality_manager`, `admin` |
| Import external events (API) | `integration_admin`, `admin` |
| View correlation candidates | `quality_analyst`, `quality_manager`, `infection_prevention`, `admin` |
| Run correlation engine | `quality_manager`, `admin` |
| View dashboard | `quality_analyst`, `quality_manager`, `admin` |
| Update correlation candidate review status | `quality_manager`, `admin` |

All endpoints require enterprise authentication (`require_enterprise_auth`). Role enforcement is applied at the route level.

---

## 3. Minimum Necessary Data

LumenAI stores only the minimum fields required to identify potential instrument-quality associations.

### SPD Tracking Fields Stored
- instrument_id, UDI, barcode, QR code, keydot_id
- tray_id, tray_name, service_line
- event_type, event_timestamp
- sterilization_status, cycle_type, cycle_status
- vendor_id
- source_system, source_record_id

### Quality Safety Fields Stored
- event_type, event_category, event_severity
- instrument_reference (instrument identifier only — no patient link)
- tray_reference
- capa_id, rca_status
- source_system, source_record_id, event_timestamp

### Fields NEVER Stored
- patient_id, mrn, medical_record_number
- date_of_birth
- patient_name, first_name, last_name
- SSN or other government identifiers
- Address, phone number, email address
- Admission/discharge dates (only procedure-level timestamps)

---

## 4. PHI Avoidance Strategy

### Layer 1: Source System Responsibility
Source systems (SafeCare, ICNet, etc.) are contractually required to de-identify records before transmission. LumenAI BAA language requires this.

### Layer 2: Application-Layer Enforcement
- `de_identified = True` is hardcoded in all QualitySafetyEventRecord and InfectionPreventionEventRecord inserts
- The import endpoint strips any incoming fields matching the PHI prohibited list before processing
- PHI prohibited fields: `patient_id`, `mrn`, `dob`, `patient_name`, `name`, `ssn`

### Layer 3: Schema-Level Prevention
No PHI field columns exist in any P17 model. The schema itself cannot store PHI even if the application layer were bypassed.

### Layer 4: Audit Detection
All imports are audited. Unexpected PHI discovery triggers the incident response process below.

---

## 5. De-identification Strategy

1. Source system applies de-identification per their HIPAA-compliant process
2. LumenAI connector strips any residual PHI fields on receipt (see PHI prohibited list)
3. LumenAI stores `de_identified = True` flag on all quality/IP records
4. `raw_payload_hash` (SHA-256) is stored for audit traceability without retaining the payload
5. Instrument identifiers (UDI, barcode) are retained as they are device identifiers, not patient identifiers

---

## 6. Audit Logging

Every import run, correlation run, and connection test is logged to the LumenAI audit log with:
- `tenant_id` and `tenant_name`
- `actor_email` (authenticated user)
- `action_type` (e.g., `integrations.systems.run_import`)
- `resource_type` and `resource_id`
- Timestamp (automatic)
- Relevant details (record counts, system name, etc.)

Audit logs are immutable and retained per the LumenAI data retention policy.

---

## 7. Import Provenance

Every imported record stores a `raw_payload_hash` field containing the SHA-256 hash of the serialized incoming payload. This enables:
- Audit traceability without retaining the full payload
- Detection of duplicate imports
- Evidence of what was received at import time

The original payload is NOT stored (minimum necessary data principle).

---

## 8. Connector Credential Handling

Credentials are NEVER stored in:
- The `ExternalSystemConnection` table
- The `config_json` field
- Application source code
- Git repositories

Credentials MUST be stored in:
- Environment variables (development/staging)
- Secret manager (AWS Secrets Manager, Azure Key Vault, GCP Secret Manager) in production

The `auth_type` field records only the authentication mechanism type (e.g., `oauth2`, `api_key`). The connector retrieves credentials at runtime from environment variables using a well-known naming convention (e.g., `CENSITRAC_API_KEY`, `ICNET_CLIENT_SECRET`).

---

## 9. Business Associate Considerations

Any external system that may transmit PHI to LumenAI requires:
- A signed Business Associate Agreement (BAA) before integration goes live
- Confirmation that de-identification is applied before data leaves the source system
- Annual review of BAA terms and system data flows

Systems transmitting de-identified data only (post de-id by source) may not require a BAA but require legal review on a case-by-case basis.

LumenAI maintains a BAA registry. No integration may go live without appropriate legal documentation.

---

## 10. Incident Response

### Data Quality Errors
1. Alert integration_admin and quality_manager via notification channel
2. Suspend failing import run; mark status = "failed"
3. Log all details to audit log
4. Investigate root cause before resuming

### Unexpected PHI Discovery
1. **Immediately** suspend the affected connector (set connection_status = "disabled")
2. Alert Privacy Officer and Security team within 1 hour
3. Do NOT log the PHI to audit logs — log only that PHI was detected and connector was suspended
4. Initiate PHI breach assessment per HIPAA Breach Notification Rule
5. Work with source system vendor to remediate de-identification failure before re-enabling connector

### Connector Failures
1. Increment `consecutive_errors` counter on ExternalSystemConnection
2. After 3 consecutive errors: auto-disable connector (connection_status = "error")
3. Alert integration_admin
4. Manual investigation and re-enablement required

### Tenant Data Contamination
If records are found in a tenant's dataset that belong to another tenant:
1. Immediately quarantine affected records
2. Alert Security team
3. Root cause analysis within 24 hours
4. Remediation and re-validation before restoring access
