# Baseline-Aware Inspection Payload Contract

## Purpose

LumenAI inspection ingestion must keep the frontend, backend, future database fields, and ranking workflow aligned around a single baseline-aware contract. The workflow is:

1. Identify the instrument through scan or manual identity fields.
2. Check the vendor or manufacturer baseline status.
3. Rank the finding as baseline-confirmed, provisional, manual-review-required, or pending baseline check.

This document captures the current frontend-to-backend payload shape and the backend-resolved ranking fields introduced across the pilot baseline patches.

## Current Implementation References

Frontend source page:

- `frontend/src/pages/NewInspectionPage.tsx`

Backend files:

- `backend/app/core/baseline_ranking_contract.py`
- `backend/app/routes/inspect.py`

The frontend currently submits instrument identity and baseline context fields. The backend baseline ranking utility resolves those fields into a normalized ranking contract. Inspection ingestion accepts the optional baseline context and returns the resolved baseline ranking fields in the response when baseline context is submitted.

## Instrument Identity Fields

These fields identify the inspected instrument. They may come from barcode, QR code, KeyDot / 2D Dot, or manual entry.

| Field | Purpose |
| --- | --- |
| `capture_method` | Selected capture path, such as Barcode, QR Code, KeyDot / 2D Dot, or Manual Entry. |
| `barcode_value` | Barcode scan value when barcode capture is used. |
| `qr_code_value` | QR code scan value when QR capture is used. |
| `keydot_value` | KeyDot / 2D Dot value when dot capture is used. |
| `catalog_number` | Manufacturer or vendor catalog number. |
| `model_number` | Manufacturer or vendor model number. |
| `manufacturer` | Manufacturer name when known. |
| `vendor` | Vendor name when known. |
| `instrument_name` | Human-readable instrument name. |
| `instrument_category` | Operational category for grouping and analytics. |

## Baseline Fields Submitted by Frontend

These fields describe what the frontend currently knows about instrument matching and vendor baseline status.

| Field | Purpose |
| --- | --- |
| `instrument_match_status` | Match state, such as Matched, Partial Match, Not Matched, or Not Checked. |
| `baseline_status` | Vendor baseline state, such as Approved Baseline Found, Pending Baseline Review, No Approved Baseline, Baseline Not Available, or Not Checked. |
| `baseline_source` | Source used for the baseline decision, such as Vendor Baseline or None. |
| `baseline_confidence` | Confidence label, such as High, Medium, Unknown. |
| `ranking_mode` | Frontend display ranking mode before backend normalization. |
| `baseline_review_required` | Frontend display value for whether baseline review is required. |

## Backend-Resolved Fields

The backend resolves baseline status into these normalized fields:

| Field | Purpose |
| --- | --- |
| `ranking_mode` | Canonical ranking mode after backend contract resolution. |
| `baseline_review_required` | Boolean indicating whether baseline review is required before final ranking. |
| `final_ranking_allowed` | Boolean indicating whether a final baseline-confirmed ranking is allowed. |
| `baseline_review_reason` | Human-readable reason for the backend decision. |

## Ranking Modes

Supported ranking modes:

- `Baseline-confirmed ranking`
- `Provisional ranking`
- `Manual review required`
- `Pending baseline check`

## Expected Backend Behavior

### Approved Baseline Found + Matched

When `baseline_status` is `Approved Baseline Found` and `instrument_match_status` is `Matched`:

```json
{
  "ranking_mode": "Baseline-confirmed ranking",
  "baseline_review_required": false,
  "final_ranking_allowed": true,
  "baseline_review_reason": "Approved baseline matched."
}
```

### Pending Baseline Review

When `baseline_status` is `Pending Baseline Review`:

```json
{
  "ranking_mode": "Provisional ranking",
  "baseline_review_required": true,
  "final_ranking_allowed": false,
  "baseline_review_reason": "Baseline pending approval; ranking remains provisional."
}
```

### No Approved Baseline or Baseline Not Available

When `baseline_status` is `No Approved Baseline` or `Baseline Not Available`:

```json
{
  "ranking_mode": "Manual review required",
  "baseline_review_required": true,
  "final_ranking_allowed": false,
  "baseline_review_reason": "No approved baseline available for final ranking."
}
```

### Not Checked, Missing, or Unknown Baseline

When `baseline_status` is missing, `Not Checked`, or unknown:

```json
{
  "ranking_mode": "Pending baseline check",
  "baseline_review_required": true,
  "final_ranking_allowed": false,
  "baseline_review_reason": "Baseline status has not been confirmed."
}
```

## Example Payloads

### Approved Stryker Kerrison Example

```json
{
  "facility": "ORC",
  "department": "Prep and Pack",
  "tray_name": "Spine tray",
  "finding_type": "Rust",
  "risk_level": "High",
  "capture_method": "Barcode",
  "barcode_value": "STRYKER-BARCODE-001",
  "qr_code_value": "",
  "keydot_value": "",
  "catalog_number": "STR-KR-001",
  "model_number": "KR-45",
  "manufacturer": "Stryker",
  "vendor": "Stryker",
  "instrument_name": "Kerrison Rongeur",
  "instrument_category": "Spine",
  "instrument_match_status": "Matched",
  "baseline_status": "Approved Baseline Found",
  "baseline_source": "Vendor Baseline",
  "baseline_confidence": "High",
  "ranking_mode": "Baseline-confirmed ranking",
  "baseline_review_required": "No"
}
```

Expected backend-resolved fields:

```json
{
  "ranking_mode": "Baseline-confirmed ranking",
  "baseline_review_required": false,
  "final_ranking_allowed": true,
  "baseline_review_reason": "Approved baseline matched."
}
```

### Pending Aesculap Forceps Example

```json
{
  "facility": "St. Francis",
  "department": "Sterile Storage",
  "tray_name": "General tray",
  "finding_type": "Discoloration",
  "risk_level": "Medium",
  "capture_method": "Manual Entry",
  "barcode_value": "",
  "qr_code_value": "",
  "keydot_value": "",
  "catalog_number": "AES-FORCEPS-DEMO",
  "model_number": "",
  "manufacturer": "Aesculap",
  "vendor": "Aesculap",
  "instrument_name": "Forceps",
  "instrument_category": "General",
  "instrument_match_status": "Partial Match",
  "baseline_status": "Pending Baseline Review",
  "baseline_source": "Vendor Baseline",
  "baseline_confidence": "Medium",
  "ranking_mode": "Provisional ranking",
  "baseline_review_required": "Yes"
}
```

Expected backend-resolved fields:

```json
{
  "ranking_mode": "Provisional ranking",
  "baseline_review_required": true,
  "final_ranking_allowed": false,
  "baseline_review_reason": "Baseline pending approval; ranking remains provisional."
}
```

### No Approved Baseline Example

```json
{
  "facility": "Memorial Regional",
  "department": "Decontamination",
  "tray_name": "Laparoscopic tray",
  "finding_type": "Blood",
  "risk_level": "Critical",
  "capture_method": "QR Code",
  "barcode_value": "",
  "qr_code_value": "UNKNOWN-QR-042",
  "keydot_value": "",
  "catalog_number": "",
  "model_number": "",
  "manufacturer": "Unknown",
  "vendor": "Unknown",
  "instrument_name": "Laparoscopic grasper",
  "instrument_category": "Laparoscopic",
  "instrument_match_status": "Not Matched",
  "baseline_status": "No Approved Baseline",
  "baseline_source": "None",
  "baseline_confidence": "Unknown",
  "ranking_mode": "Manual review required",
  "baseline_review_required": "Yes"
}
```

Expected backend-resolved fields:

```json
{
  "ranking_mode": "Manual review required",
  "baseline_review_required": true,
  "final_ranking_allowed": false,
  "baseline_review_reason": "No approved baseline available for final ranking."
}
```

### Missing or Not Checked Baseline Example

```json
{
  "facility": "Southside",
  "department": "Prep and Pack",
  "tray_name": "Orthopedic tray",
  "finding_type": "Lint",
  "risk_level": "Low",
  "capture_method": "Manual Entry",
  "barcode_value": "",
  "qr_code_value": "",
  "keydot_value": "",
  "catalog_number": "",
  "model_number": "",
  "manufacturer": "",
  "vendor": "Pilot Vendor",
  "instrument_name": "Clamp",
  "instrument_category": "Orthopedic",
  "instrument_match_status": "Not Checked",
  "baseline_status": "Not Checked",
  "baseline_source": "None",
  "baseline_confidence": "Unknown",
  "ranking_mode": "Pending baseline check",
  "baseline_review_required": "Unknown"
}
```

Expected backend-resolved fields:

```json
{
  "ranking_mode": "Pending baseline check",
  "baseline_review_required": true,
  "final_ranking_allowed": false,
  "baseline_review_reason": "Baseline status has not been confirmed."
}
```

## Current Limitations

- Baseline records are not yet persisted with inspection records.
- Vendor baseline lookup is still frontend pilot/sample logic.
- Database columns for baseline context are not yet added.
- Backend contract resolution is wired into inspection ingestion, but persistence expansion is a future patch.
- Barcode, QR, and KeyDot / 2D Dot scan hardware integration is not yet implemented.
- Findings Queue and analytics pages do not yet display baseline status or ranking mode as persisted backend data.

## Recommended Next Patches

1. Persist baseline fields on inspection records.
2. Add a vendor baseline lookup endpoint.
3. Add barcode, QR, and KeyDot / 2D Dot scanner capture support.
4. Add baseline comparison response fields to the Findings Queue.
5. Add analytics by baseline status and ranking mode.

## Review Note

This document describes the pilot payload and ranking contract as implemented today. It is not a database schema specification, endpoint redesign, or certification claim.
