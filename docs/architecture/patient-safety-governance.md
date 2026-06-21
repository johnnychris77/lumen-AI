# Patient Safety Intelligence — Governance Policy

---

## 1. Association vs Causation — Core Policy

**LumenAI NEVER claims causation between instrument quality signals and patient harm events.**

This is a foundational, non-negotiable design principle. The Patient Safety Intelligence Layer is a quality improvement tool that surfaces *potential associations* for qualified human review. It does not replace clinical or quality professional judgment.

### Required Language

All signals, API responses, dashboards, reports, and communications must use qualified association language:

| Approved | Context |
|---|---|
| "potential association" | Describing a link between a signal and an event |
| "flagged for review" | Describing the signal's status |
| "review candidate" | Describing an instrument or event |
| "may be associated" | Describing a possible relationship |
| "linked for investigation" | Describing the purpose of the signal |
| "flagged for human review" | Describing the required next step |

### Prohibited Language

The following terms are **prohibited** in all system outputs, documentation, and communications:

| Prohibited | Reason |
|---|---|
| "caused" | Implies established causation |
| "resulted in" | Implies directional causation |
| "responsible for" | Implies liability assignment |
| "proven link" | Implies established evidence |
| "confirmed association" (without human review) | System cannot confirm — only humans can |
| "definitive evidence" | Beyond system scope |

### Code Enforcement

The `association_reason` and `recommended_review_action` fields in all signal models are pre-populated with approved language templates. New templates must be reviewed against this policy before deployment.

---

## 2. Human Review Requirement

**All signals require human clinical and quality review before any action is taken.**

- Every signal model has `human_review_required = True` (set at creation, not overridable by API)
- Every signal enters the review queue with `human_review_status = "pending"`
- Signals must not be acted upon (quarantine, recall, CAPA initiation) based solely on automated output
- Review workflow: `pending → under_review → reviewed → closed`

### Review Workflow

```
Signal Created (human_review_status = "pending")
        │
        ▼
Quality/Clinical Professional assigns:
  human_review_status = "under_review"
  reviewed_by = actor_email
        │
        ▼
Review complete:
  human_review_status = "reviewed"
  reviewed_at = timestamp
  [decision documented outside system or in CAPA]
        │
        ▼
Case closed:
  human_review_status = "closed"
```

---

## 3. Audit Trail

Every patient safety intelligence action creates an immutable audit event.

### Logged Events

| Action | `action_type` |
|---|---|
| View signal list | `patient_safety.signals.list` |
| View signal detail | `patient_safety.signals.detail` |
| Run correlation engine | `patient_safety.correlate` |
| View near misses | `patient_safety.near_misses.list` |
| View quality investigations | `patient_safety.quality_investigations.list` |
| View executive risks | `patient_safety.executive_risk.list` |
| Import external events | `patient_safety.events.import` |
| View dashboard | `patient_safety.dashboard.view` |
| View infection prevention signals | `patient_safety.infection_prevention.list` |
| View CAPA effectiveness | `patient_safety.capa_effectiveness.list` |

### Audit Record Contents

Each audit event includes:
- `tenant_id` — tenant scope
- `actor_email` — authenticated user
- `action_type` — action identifier
- `resource_type` — affected resource class
- `resource_id` — affected resource identifier
- `details` — action-specific metadata
- `timestamp` — UTC timestamp (server-side)
- `status` — success / failure

Audit records are immutable and cannot be deleted via API.

---

## 4. Privacy Controls

### No Patient Identifiers

No signal model stores patient identifiers. The following fields are **explicitly prohibited** in all signal and import models:

- `patient_id`
- `mrn` (Medical Record Number)
- `dob` (Date of Birth)
- `patient_name`
- `ssn` (Social Security Number)
- Any HIPAA-defined Protected Health Information (PHI)

### De-identification

External events from quality reporting and infection prevention systems must be de-identified before import:

1. Connector strips all patient identifiers from the payload
2. `de_identified = True` flag is set on the `ExternalEventImport` record
3. Raw payload is not stored — only the SHA-256 hash for audit integrity
4. Events where de-identification cannot be confirmed (`de_identified = False`) must not be imported

### Instrument and Procedure Context

The following non-patient quality markers are retained:
- Instrument ID / UDI / barcode
- Procedure type category (not patient-specific)
- Pathogen name (organism level, not patient level)
- Tray / set identifier

---

## 5. Tenant Isolation

Patient safety signals are strictly scoped to the authenticated tenant:

- Every model has `tenant_id` as a mandatory, indexed field
- All API queries filter by `tenant_id` derived from `get_request_tenant_id(request)`
- No cross-tenant query is possible via the API layer
- Cross-tenant signal aggregation is only available through the anonymised National Network (P15), which suppresses records below N=3

---

## 6. Export Controls

- Signal data exports require an audit log entry at time of export
- Raw signal export (full dataset) is gated by enterprise tier entitlement
- Export files must not contain patient identifiers
- Export events are logged with `actor_email` and timestamp

---

## 7. Investigation Workflow

Quality investigations follow a defined lifecycle:

```
QualityInvestigation.investigation_status:
  open → in_progress → closed

QualityInvestigation.human_review_status:
  open → in_progress → closed

CAPAEffectivenessSignal.capa_status:
  open → effective | ineffective → closed
```

Investigations cannot be deleted; they can only be closed. The `closed_at` timestamp is immutable once set.

---

## 8. Disclaimer Requirements

Every API response and dashboard surface must include the following disclaimer:

> *"These signals represent potential associations for human review. They do not establish causation."*

This disclaimer is:
- Returned in every list and detail endpoint response
- Displayed on every dashboard view
- Included in any exported signal dataset
- Non-removable via configuration

---

## 9. Legal Safe Harbor

The Patient Safety Intelligence Layer is designed as a quality improvement tool intended to operate within the protections of the **Patient Safety and Quality Improvement Act of 2005 (PSQIA)**, 42 U.S.C. §§ 299b-21 to 299b-26.

Key design decisions supporting PSQIA compliance:
- All signals are designated as quality improvement data, not clinical records
- No signal constitutes a medical determination or clinical finding
- Human review is mandatory before any operational decision
- The system does not generate incident reports — it flags potential associations for qualified staff to review using their own reporting systems
- No causation language is ever used in system outputs

> **Note**: Facilities implementing LumenAI should consult their legal counsel and Patient Safety Organization (PSO) regarding PSQIA privilege and protection for their specific use case. LumenAI does not provide legal advice.
