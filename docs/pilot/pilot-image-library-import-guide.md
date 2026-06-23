# LumenAI Pilot Image Library — Import Guide

Version: 1.0  
Applies to: Phase 4 pilot image collection (~100 lumened surgical instrument images)

---

## Overview

This guide covers how to organize, name, and import the 100 pilot lumened instrument images into the LumenAI Demo Image Library. Following these conventions ensures images load correctly in the UI, metadata matches the CV pipeline schema, and the baseline–inspection pairing logic works.

---

## 1. Folder Structure

Organize images before upload using this folder layout:

```
pilot-images/
├── baselines/
│   ├── approved/          ← images that have passed SPD manager review
│   └── draft/             ← pending review
├── inspections/
│   ├── pass/              ← no findings detected
│   └── findings/
│       ├── blood/
│       ├── bone/
│       ├── tissue/
│       ├── debris/
│       ├── corrosion/
│       ├── crack/
│       └── insulation_damage/
├── borescope/             ← borescope-only images (channel / lumen views)
└── metadata/
    └── pilot-images.csv   ← one row per image (see §4)
```

> **Note:** Do not place images directly in root `pilot-images/`. Subfolders drive the automatic `image_type` and `finding_category` classification during batch import.

---

## 2. File Naming Convention

### Pattern

```
{facility}_{instrument}_{model}_{identifier}_{imageType}_{findingCategory}_{YYYYMMDD}.{ext}
```

### Rules

| Segment | Required | Format | Example |
|---|---|---|---|
| `facility` | Yes | lowercase, hyphens | `bonsecours`, `mercy-health` |
| `instrument` | Yes | lowercase, hyphens | `laparoscopic-grasper`, `needle-driver` |
| `model` | Yes | lowercase, hyphens | `model-26173ka`, `ref-0090` |
| `identifier` | Yes | type-value | `keydot-127`, `qr-4892b`, `barcode-a04421` |
| `imageType` | Yes | one of: `baseline`, `inspection`, `borescope`, `finding` | `baseline` |
| `findingCategory` | Yes | one of: `none`, `blood`, `bone`, `tissue`, `debris`, `corrosion`, `crack`, `insulation-damage`, `other` | `none` |
| `YYYYMMDD` | Yes | ISO date with no separators | `20260622` |
| extension | Yes | `.jpg` or `.png` or `.webp` | `.jpg` |

### Examples

```
# Clean baseline
bonsecours_laparoscopic-grasper_model-26173ka_keydot-127_baseline_none_20260622.jpg

# Tissue finding on inspection
mercy-health_needle-driver_model-maj1262_barcode-a04421_finding_tissue_20260514.jpg

# Borescope lumen view, no finding
bonsecours_suction-irrigator_model-ref0090_qr-7731c_borescope_none_20260618.jpg

# Crack finding
bonsecours_scissors-metzenbaum_model-110218_keydot-341_finding_crack_20260512.jpg
```

> **Critical:** Segment order must be exact. The batch import script parses segments by position. Extra underscores in instrument names or model numbers must be replaced with hyphens.

---

## 3. Identifier Types

| Type | Prefix | Description |
|---|---|---|
| KeyDot | `keydot-` | Micro-dot laser-encoded identifier |
| QR code | `qr-` | QR code value or UDI string |
| Barcode | `barcode-` | 1D barcode value |
| Manual | `manual-` | Human-assigned identifier when no machine-readable tag exists |

---

## 4. Metadata CSV Structure

Create one CSV file at `pilot-images/metadata/pilot-images.csv` with one row per image.

### Required columns

| Column | Type | Description |
|---|---|---|
| `file_name` | string | Exact file name including extension |
| `instrument_name` | string | Human-readable instrument name |
| `manufacturer` | string | Manufacturer name |
| `model` | string | Model number or code |
| `identifier` | string | Full identifier value (e.g. `keydot-127`) |
| `identifier_type` | enum | `keydot` \| `qr` \| `barcode` \| `manual` |
| `image_type` | enum | `baseline` \| `inspection` \| `borescope` \| `finding` |
| `finding_category` | enum | `none` \| `blood` \| `bone` \| `tissue` \| `debris` \| `corrosion` \| `crack` \| `insulation_damage` \| `other` |
| `risk_level` | enum | `low` \| `medium` \| `high` \| `critical` |
| `baseline_status` | enum | `approved` \| `pending_review` \| `draft` |
| `image_quality` | enum | `high` \| `medium` \| `low` |
| `capture_date` | date | `YYYY-MM-DD` |
| `capture_device` | string | Device name (e.g. `Borescope Pro 3000`) |
| `capture_angle` | string | Free text description |
| `notes` | string | Clinical notes (quoted if contains commas) |

### Optional columns

| Column | Type | Description |
|---|---|---|
| `known_normal_characteristics` | string | Baseline only: normal appearance description |
| `known_abnormal_characteristics` | string | Baseline only: known defect patterns |
| `paired_baseline_file` | string | For inspection images: file name of matching baseline |
| `uploaded_by` | string | Technician name or ID |

### Example CSV (first 3 rows)

```csv
file_name,instrument_name,manufacturer,model,identifier,identifier_type,image_type,finding_category,risk_level,baseline_status,image_quality,capture_date,capture_device,capture_angle,notes
bonsecours_laparoscopic-grasper_model-26173ka_keydot-127_baseline_none_20260622.jpg,Laparoscopic Grasper,Storz,26173KA,keydot-127,keydot,baseline,none,low,approved,high,2026-06-22,Borescope Pro 3000,"distal tip, 0°","Clean. Jaws close flush. No residue."
mercy-health_needle-driver_model-maj1262_barcode-a04421_finding_tissue_20260514.jpg,Needle Driver,Olympus,MAJ-1262,barcode-A04421,barcode,finding,tissue,high,approved,high,2026-05-14,Borescope Pro 3000,"jaw hinge","Tissue fragment at jaw hinge. Requires re-cleaning."
bonsecours_suction-irrigator_model-ref0090_qr-7731c_borescope_none_20260618.jpg,Suction Irrigator,Medtronic,REF-0090,qr-7731-C,qr,borescope,none,low,approved,high,2026-06-18,Rigid Borescope 4 mm,"lumen distal","Clear lumen. No occlusion or residue."
```

---

## 5. Baseline–Inspection Pairing

For the CV comparison to work, each inspection image should be paired with its matching baseline via:

1. **Shared identifier** — both baseline and inspection images have the same `identifier` value (e.g. `keydot-127`). The pipeline joins on identifier automatically.
2. **`paired_baseline_file` column** in the CSV — explicit override when the identifier-based join is ambiguous.

> If an instrument has multiple baseline images (different angles), select the closest angle match in `paired_baseline_file`.

---

## 6. Upload Workflow

### Via UI (recommended for individual images)

1. Open **Baselines → Baseline Library → Upload Baseline** or navigate to `/baseline-image-upload`
2. Complete instrument identification fields
3. Drag-and-drop or browse for the image
4. Set capture metadata (device, angle, quality)
5. Document normal and abnormal characteristics
6. Submit — image enters `pending_review` queue

### Via Inspection Upload (for inspection / finding images)

1. Navigate to `/inspection-image-upload`
2. Complete instrument identification
3. Upload inspection images + borescope images
4. Classify finding category and risk level
5. Submit — image is SHA-256 hashed and queued for CV pipeline

### Batch import (for 100-image pilot load)

The batch import script reads the metadata CSV and calls the upload APIs sequentially:

```bash
# Example curl for baseline image upload
curl -X POST "$API_BASE/api/enterprise/vendor-baseline-subscription/baselines/upload-image" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@path/to/image.jpg"

# Then create the baseline record with the returned baseline_image_url:
curl -X POST "$API_BASE/api/enterprise/vendor-baseline-subscription/baselines" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "instrument_name": "Laparoscopic Grasper",
    "manufacturer": "Storz",
    "model_number": "26173KA",
    "keydot_id": "keydot-127",
    "baseline_image_url": "<returned url>",
    "notes": "Clean. Jaws close flush."
  }'
```

---

## 7. Image Quality Checklist

Before submitting any image:

- [ ] Image is in focus — no motion blur
- [ ] Lighting is even — no overexposed highlights or crushed shadows
- [ ] Instrument fills at least 60% of the frame
- [ ] No fingers, gloves, or reflections obscuring the subject
- [ ] For borescope images: probe positioned and locked before capture
- [ ] For finding images: finding is clearly visible and centred
- [ ] File size: 500 KB – 8 MB (outside this range → compress or re-capture)
- [ ] File format: JPEG, PNG, or WebP (TIFF accepted by API but not recommended for web display)

---

## 8. Finding Severity Guidelines

Use these reference criteria when classifying `risk_level`:

| Risk Level | Criteria |
|---|---|
| `low` | No findings, or cosmetic surface marks only |
| `medium` | Minor debris or bioburden not in critical zones; early corrosion |
| `high` | Tissue / bone / blood residue; active corrosion; cracking |
| `critical` | Blood residue in lumen; full crack; insulation breach; remove from service |

> **Reminder:** All AI-generated classifications carry `human_review_required: true`. This guide's `risk_level` field is the technician's initial classification — final determination requires SPD manager sign-off.

---

## 9. Suggested Pilot Image Distribution

For 100 pilot images across instrument types and finding categories:

| Category | Count | Notes |
|---|---|---|
| Baselines (approved) | 25 | Mix of instrument types, various angles |
| Baselines (pending / draft) | 5 | For testing review workflow |
| Inspections — pass | 20 | No findings, routine inspections |
| Finding — blood | 10 | Critical category |
| Finding — bone | 8 | High priority |
| Finding — tissue | 8 | High priority |
| Finding — debris | 8 | Medium priority |
| Finding — corrosion | 8 | Medium priority |
| Finding — crack | 5 | Critical category |
| Finding — insulation damage | 3 | High priority |

---

## 10. Support

For image upload issues, contact the LumenAI technical team.  
For clinical classification questions, contact your SPD Quality Manager.

Do **not** submit images containing patient-identifiable information.  
Do **not** include facility name in image pixels — only in the file name.
