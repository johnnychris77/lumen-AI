# Baseline Governance Standard

**Version:** 1.0
**Status:** Published
**Maintained by:** GSIN Governance Board & Data Standards Working Group

---

## Purpose

This standard defines the governance framework for the creation, approval, versioning, provenance tracking, and audit of instrument quality baselines within the Global Surgical Intelligence Network. It ensures baseline data integrity, traceability, and compliance with applicable data standards.

**Disclaimer:** All baseline governance outputs require human review before operational decisions. Does not constitute regulatory approval or clearance.

---

## 1. Baseline Approval Framework

### What Requires Approval

Any baseline that will be referenced for cross-network benchmarking or network publication requires formal governance approval:

| Baseline Type | Approval Level | Reviewer |
|---------------|---------------|----------|
| Manufacturer-published baseline | Standard approval | Quality Manager + Admin |
| Network-contributed baseline | Enhanced approval | Admin + Executive + Governance Board review |
| Clinical study baseline | Enhanced approval | Clinical reviewer + Admin + Governance Board |
| Regulatory guidance baseline | Administrative confirmation | Admin |

### Approval Workflow

```
Submission (manager/admin) →
k-Anonymity Verification (≥5 contributing facilities) →
Provenance Review →
Quality Manager Review →
Executive Sign-off (if network-contributed or clinical) →
Governance Board Ratification (if publishing to network) →
Published
```

### Approval Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Submitted, awaiting first review |
| `approved` | Approved and active |
| `rejected` | Rejected with notes; resubmission possible |
| `deprecated` | Superseded by a newer version; archived |

---

## 2. Version Control Framework

### Versioning Schema

Baselines follow semantic versioning: **MAJOR.MINOR**

- **MAJOR** increment: Criteria change, instrument category change, or regulatory realignment
- **MINOR** increment: Data update, editorial correction, additional facility contribution

### Version Lifecycle

```
1.0 (Published) → 1.1 (Minor update) → 2.0 (Major revision) → 1.x (Deprecated)
```

### Version Change Requirements

| Change Type | Required Documentation |
|-------------|----------------------|
| Minor (x.Y) | Change rationale, contributing facilities count, delta summary |
| Major (X.0) | Full governance review, public comment period (if network-published), regulatory alignment review |
| Deprecation | Deprecation notice, supersession reference, archive date |

### Retention Policy

- Active baselines: Retained indefinitely
- Deprecated baselines: Archived for minimum 7 years (regulatory compliance)
- Version history: Immutable audit trail maintained in perpetuity

---

## 3. Provenance Framework

### Provenance Sources

All baselines must declare a provenance source:

| Source | Description | k-Anonymity Requirement |
|--------|-------------|------------------------|
| `manufacturer_data` | Data published by instrument manufacturer | ≥1 (single source; manufacturer verification required) |
| `network_contributed` | Aggregated from GSIN participant submissions | ≥5 contributing facilities |
| `clinical_study` | Derived from published clinical research | Citation required; institutional approval |
| `regulatory_guidance` | Published by a recognized regulatory body | Reference to official guidance document |

### Provenance Record Contents

Each baseline must include:
- Source type
- Contributing facilities count (where applicable)
- Data collection period
- k-anonymity verification status
- Data Processing Agreement reference (for network-contributed)
- Change rationale (for version updates)

### Privacy Constraints

- No individual facility, patient, or instrument is identified in any baseline record
- Contributing facilities count must meet k-anonymity floor before network publication
- All provenance records are audit-logged with `compliance_flag=True`

---

## 4. Audit Framework

### What Is Audited

Every baseline governance event generates an immutable audit log entry:

| Event | Audit Fields |
|-------|-------------|
| Baseline submission | Submitter, governance_type, instrument_category, timestamp |
| Approval decision | Approver, decision, notes, timestamp |
| Version change | From_version, to_version, change_rationale, timestamp |
| Deprecation | Deprecation reason, supersession reference, timestamp |
| Network publication | Publishing approver, k-anonymity verification, timestamp |

### Audit Log Guarantees

- All audit records are `compliance_flag=True`
- Audit records are append-only — no modification or deletion
- Every governance actor is identified (email) in the audit trail
- Records are retained per regional data retention requirements (minimum 7 years)

### Audit Access

- Quality managers: Read their own tenant's governance history
- Administrators: Full read access to tenant governance history
- Governance Board: Read access to aggregated (anonymized) network governance metrics

---

## 5. Governance Roles

| Role | Permissions |
|------|-------------|
| Quality Manager | Submit governance records, view own tenant history |
| Administrator | Submit + approve governance records, view tenant history |
| Executive | Approve governance records, view dashboard |
| Governance Board | Ratify network-published baselines, access network-level audit summaries |

---

## 6. Compliance Mapping

| Requirement | Framework | Baseline Governance Controls |
|-------------|-----------|------------------------------|
| Data integrity | ISO 13485 §4.2.5 | Immutable audit trail, version control |
| Traceability | FDA 21 CFR 820 | Provenance records, approval chain |
| Post-market surveillance | EU MDR Article 83 | Version history, deprecation records |
| Privacy | GDPR / HIPAA / PDPA | k-anonymity, DPA references, audit logs |

---

*Human review required before any operational decisions. Does not constitute regulatory approval or clearance.*
