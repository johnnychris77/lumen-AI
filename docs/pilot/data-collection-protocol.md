# LumenAI Pilot Data Collection Protocol

**Version:** 1.0  
**Effective Date:** 2026-06-21  
**Owner:** Quality & Compliance  

---

## 1. Purpose

This protocol defines the required data fields, collection procedures, validation rules, and quality requirements for instrument inspection data collected during the LumenAI pilot program. Adherence ensures data is sufficient for quality analysis and meets the data governance obligations of the pilot agreement.

---

## 2. Required Data Fields per Inspection Record

### 2.1 Instrument Identification

| Field | Required | Validation Rule | Notes |
|-------|----------|----------------|-------|
| `instrument_type` | Mandatory | Must match approved dropdown values | e.g., "Laparoscopic Grasper", "Retractor" |
| `vendor_name` | Recommended | Free text, max 100 chars | Instrument manufacturer |
| `material_type` | Mandatory | Must match approved dropdown values | e.g., "stainless_steel", "titanium" |
| `site_name` | Mandatory | Free text, max 100 chars | Submitting facility name |

### 2.2 Inspection Findings

| Field | Required | Validation Rule | Notes |
|-------|----------|----------------|-------|
| `stain_detected` | Mandatory | Boolean (true/false) | Primary quality indicator |
| `confidence` | Optional | Float 0.0–100.0 | Technician confidence in finding |
| `detected_issue` | Mandatory | Must match approved dropdown values | e.g., "blood", "crack", "corrosion" |
| `risk_score` | Optional | Float 0.0–1.0 | System-assigned; do not manually enter |

### 2.3 Processing Metadata

| Field | Required | Validation Rule | Notes |
|-------|----------|----------------|-------|
| `inference_mode` | System | Assigned by system | "manual" for pilot entries |
| `model_name` | System | Assigned by system | Populated automatically |
| `model_version` | System | Assigned by system | Populated automatically |
| `status` | Mandatory | One of: pending, reviewed, flagged, closed | Default: pending |

### 2.4 Audit Fields (System-Assigned)

| Field | Assigned By | Notes |
|-------|-------------|-------|
| `id` | Database | Auto-increment |
| `created_at` | System | UTC timestamp at submission |
| `tenant_id` | Auth system | From authenticated session token |
| `inference_timestamp` | System | UTC timestamp of analysis |

---

## 3. Data Collection Procedure

### 3.1 When to Log an Inspection

Log an inspection record for each instrument that undergoes a quality check at any of the following touchpoints:

- Post-decontamination visual inspection
- Pre-sterilization verification
- Post-sterilization release check
- Any inspection triggered by a quality concern

### 3.2 Timing Requirements

- Inspection record must be submitted **within 4 hours** of the physical inspection
- Batch submissions at end of shift are acceptable for the pilot period
- Do not back-date submissions — use actual inspection timestamp

### 3.3 Multi-Finding Records

If an instrument has multiple issues observed:
- Select **all** applicable findings in the multi-select checkbox
- A single inspection record can have multiple `detected_issue` values
- Do not split into multiple records for the same inspection event

### 3.4 Image Submission

Images are strongly encouraged but not required during the pilot:
- Capture image immediately after physical inspection, before instrument is moved
- Standard lighting required (no shadows across inspection area)
- Minimum resolution: 1200 × 900 pixels
- Maximum file size: 10 MB per image
- Accepted formats: JPEG, PNG, WEBP, TIFF
- Images are hashed (SHA-256) — original files are not stored in the database

---

## 4. Data Quality Rules

### 4.1 Completeness Rules

| Rule ID | Rule | Threshold |
|---------|------|-----------|
| DQ-01 | All mandatory fields populated | 100% required |
| DQ-02 | `stain_detected` field populated | 100% required |
| DQ-03 | `detected_issue` populated when stain_detected=true | 100% required |
| DQ-04 | `instrument_type` selected from approved list | 100% required |
| DQ-05 | `site_name` populated | 100% required |

### 4.2 Consistency Rules

| Rule ID | Rule | Action on Failure |
|---------|------|------------------|
| DQ-10 | `stain_detected=true` must have at least one `detected_issue` selected | Block submission |
| DQ-11 | `confidence` must be 0–100 if provided | Block submission |
| DQ-12 | `risk_score` must be 0.0–1.0 if present | System enforced |
| DQ-13 | `tenant_id` must match authenticated session | System enforced |
| DQ-14 | `created_at` cannot be in the future | System enforced |

### 4.3 Volume Rules (Pilot Minimum)

| Rule ID | Rule | Target |
|---------|------|--------|
| DQ-20 | Minimum inspections per week per pilot site | ≥ 25 |
| DQ-21 | Minimum unique instrument types logged per month | ≥ 5 |
| DQ-22 | Data completeness rate (mandatory fields) | ≥ 95% |

Failure to meet volume rules for 2 consecutive weeks triggers a coordinator check-in to identify workflow barriers.

### 4.4 Prohibited Data

The following must NEVER be entered into LumenAI:
- Patient names, initials, or identifiers
- Patient MRN, DOB, or encounter numbers
- Staff names (use role/shift designations only if needed)
- Any free-text field containing PHI
- Credit card numbers, SSNs, or personal financial data

---

## 5. Data Correction Procedure

### 5.1 Minor Corrections (Within 24 Hours)

Contact your site coordinator with:
- Inspection ID (from submission confirmation)
- Field name to correct
- Current value (incorrect)
- Correct value
- Reason for correction

Corrections are logged in the audit trail with the correcting user's ID and timestamp.

### 5.2 Major Corrections (Record Invalidation)

If an entire record must be invalidated:
1. Contact LumenAI CS with inspection ID and reason
2. LumenAI support sets `status = "invalidated"` with audit note
3. Re-submit correct record within 24 hours

### 5.3 No Deletions During Pilot

Records are not deleted during the pilot period — they are invalidated and preserved for data integrity and audit purposes.

---

## 6. Pilot Data Volume Targets

| Week | Cumulative Inspections | Notes |
|------|----------------------|-------|
| 1 | ≥ 25 | Ramp-up week |
| 2 | ≥ 75 | Full workflow adoption |
| 4 | ≥ 200 | Steady state |
| 8 | ≥ 500 | Analysis-ready dataset |
| 12 | ≥ 800 | Pilot conclusion dataset |

These targets are guidelines, not contract obligations. Sites below target for 2 consecutive weeks receive additional support.
