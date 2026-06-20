# Validation Dataset Specification

## 1. Overview

This document specifies the composition, acquisition standards, annotation protocol,
and governance requirements for the LumenAI Clinical Validation Dataset used in
pre-market validation of the CV inspection module (P4) and associated clinical study
(HAIRS-001).

**Dataset name:** LUM-VALSET-001
**Version:** 1.0
**Purpose:** Pre-market clinical validation (not for model training)
**Status:** Specification — pending assembly

---

## 2. Finding Categories & Sample Requirements

| Category | Min Positive | Min Negative | Notes |
|----------|-------------|-------------|-------|
| Blood | 100 | 100 | Include dried, fresh, smeared variants |
| Bone | 100 | 100 | Fragments in serrations |
| Tissue | 100 | 100 | Soft tissue, connective tissue |
| Residue | 100 | 100 | General organic residue |
| Corrosion | 100 | 100 | Pitting, surface rust, galvanic |
| Crack | 100 | 100 | Hairline, propagating, complete |
| Pitting | 100 | 100 | Distinguish from corrosion |
| Insulation damage | 100 | 100 | Nicks, burns, delamination |
| Barcode | 100 | 100 | Readable vs. damaged |
| UDI | 100 | 100 | Complete vs. partial |
| QR | 100 | 100 | Valid vs. corrupted |
| KeyDot | 100 | 100 | Legible vs. obscured |

**Total minimum: 2,400 positive + 1,200 negative = 3,600 images**

Target with attrition buffer (20%): **4,320 images**

### 2.1 Category Definitions

**Contamination categories (blood, bone, tissue, residue):**
- Blood: Hemoglobin-containing residue; includes dried (dark brown/black),
  fresh (bright red), or smeared. Confirmed by visual inspection or protein assay.
- Bone: Mineralized tissue fragments; typically found in serrations of bone rongeurs,
  curettes, and similar instruments.
- Tissue: Soft or connective tissue; mucosa, adipose, muscle fragments.
- Residue: Non-specific organic residue not meeting blood/bone/tissue criteria;
  includes biofilm precursors.

**Structural categories (corrosion, crack, pitting, insulation):**
- Corrosion: Surface oxidation including pitting corrosion, surface rust (iron oxide),
  and galvanic corrosion at dissimilar metal junctions.
- Crack: Mechanical failure of instrument body; includes hairline cracks (< 0.5mm width),
  propagating cracks, and complete fractures.
- Pitting: Localized material loss creating surface indentations; distinguished from
  corrosion by absence of oxidation products.
- Insulation damage: Degradation of insulating coating on electrosurgical instruments;
  includes nicks, burns, delamination, and color changes indicating heat damage.

**Tracking/identification categories (barcode, udi, qr, keydot):**
- Barcode: 1D barcode label; positive = label damaged/unreadable, negative = readable.
- UDI: Unique Device Identifier marking (direct mark or label);
  positive = incomplete/unreadable, negative = complete and readable.
- QR: 2D QR code; positive = corrupted/unreadable, negative = valid scan.
- KeyDot: Proprietary dot-matrix identification system; positive = obscured/damaged,
  negative = legible and decodable.

---

## 3. Image Acquisition Standards

### 3.1 Technical Requirements
- **Resolution:** ≥ 1920×1080 pixels
- **Format:** JPEG (quality ≥ 95) or PNG (lossless)
- **Color space:** sRGB
- **Bit depth:** 8-bit per channel minimum

### 3.2 Lighting Standards
- **Illumination:** Standardized 5000K LED ring light
- **Intensity:** 50,000–80,000 lux at instrument surface
- **Uniformity:** ≤ 20% variation across instrument surface
- **Shadows:** Minimized; dual-ring configuration recommended for tubular instruments

### 3.3 Acquisition Parameters
- **Camera-to-instrument distance:** 20–30 cm
- **Depth of field:** Full instrument in focus; f/8 or higher aperture
- **Multiple angles per instrument:** 0° (top), 45° (oblique), 90° (side)
- **Instrument orientation:** Standardized positioning jig (instrument-category-specific)

### 3.4 Acquisition Protocol
1. Clean instrument inspection area (neutrally-colored matte background)
2. Position instrument in category-appropriate jig
3. Verify lighting uniformity with calibration card
4. Capture 3 angles; review for focus and exposure before proceeding
5. Log: instrument ID, category, acquisition site, date, camera settings

---

## 4. Annotation Protocol

### 4.1 Annotation Tool
- **Primary:** Label Studio (open source; self-hosted for data security)
- **Acceptable alternatives:** CVAT, VGG Image Annotator (VIA)
- **Format:** COCO JSON with bounding boxes + category labels

### 4.2 Annotation Schema
For each image:
```json
{
  "image_id": "<uuid>",
  "file_name": "<filename>",
  "finding_category": "<category>",
  "finding_present": true | false,
  "annotations": [
    {
      "bbox": [x, y, width, height],
      "category_id": <int>,
      "area": <float>,
      "annotator_id": "<anonymized>",
      "confidence": 1 | 2 | 3
    }
  ],
  "ground_truth": true | false,
  "gt_method": "consensus" | "unanimous" | "adjudicated"
}
```

### 4.3 Annotator Requirements
- Minimum 2 independent annotators per image (CRCST certified)
- At least one annotator with > 2 years SPD experience per batch
- Annotators blind to each other's annotations during initial pass
- Monthly calibration sessions with reference cases

### 4.4 Disagreement Resolution
- **Agreement:** Both annotators agree → ground truth set
- **Disagreement:** Case escalated to SPD Educator panel
- **Adjudication:** Educator provides tie-breaking annotation with rationale
- **Persistent disagreement (3-way):** CVC chair makes final determination;
  case flagged in dataset as "adjudicated"

### 4.5 Inter-Rater Reliability
- **Minimum requirement:** Cohen's kappa ≥ 0.85 between any two annotators
- **Measured:** Monthly on rotating subset (10% of new annotations)
- **Action if kappa < 0.85:** Annotator retraining + calibration session required

---

## 5. Data Governance

### 5.1 De-identification
- No hospital name, unit, or location identifiers in image metadata
- No patient identifiers (MRN, name, DOB, encounter number)
- No staff identifiers (annotator names replaced with anonymized IDs)
- EXIF data stripped from all images before annotation

### 5.2 Storage
- **Primary storage:** HIPAA-compliant encrypted AWS S3 bucket
  (server-side encryption: AES-256; KMS key managed by LumenAI)
- **Access control:** IAM roles with least-privilege; MFA required
- **Backup:** Cross-region replication to secondary bucket
- **Transfer:** TLS 1.2+ required for all data movement

### 5.3 Access Control
- Clinical validation team members only (role-based access list maintained by CVC)
- External collaborators (site coordinators, annotators): scoped access to their
  site's images only; no cross-site access
- Access log: CloudTrail enabled; all access events retained ≥ 7 years

### 5.4 Retention
- Dataset retained minimum **10 years** from date of regulatory submission
  (FDA 21 CFR Part 820.180)
- Deletion requires written authorization from Regulatory Affairs Lead and CVC Chair
- Retention log maintained in document management system

---

## 6. Dataset Splits

| Split | Proportion | Purpose | Sealed? |
|-------|-----------|---------|---------|
| Training | 70% | Internal model development | No |
| Validation | 15% | Hyperparameter tuning, interim evaluation | No |
| Test (held-out) | 15% | Final clinical validation | Yes — sealed until final validation |

**Sealed test set protocol:**
- Test set partitioned before model training begins
- Test set stored in separate access-controlled S3 prefix
- Access to test set requires dual authorization (Clinical AI Lead + CVC Chair)
- Unsealing logged with date, requestor, and justification
- Test set may only be used once per validation cycle; reuse requires CVC approval

---

## 7. Quality Checks

### 7.1 Class Balance Report
- Generated after annotation completion
- Required: no category with > 60% positive or > 70% negative prevalence
- If imbalanced: additional acquisition required before validation proceeds

### 7.2 Annotation Inter-Rater Reliability
- Cohen's kappa ≥ 0.85 required at dataset level
- Per-category kappa ≥ 0.80 required
- Report generated and signed by Clinical AI Validation Lead

### 7.3 Image Quality Filters
Automated quality checks before annotation:
- **Blur detection:** Laplacian variance < 100 → reject
- **Exposure check:** Mean pixel value < 30 or > 220 → review
- **Occlusion check:** > 20% of instrument occluded → reject
- **Duplicate detection:** Perceptual hash (pHash) similarity > 0.95 → deduplicate

### 7.4 Final Dataset Acceptance Checklist
- [ ] ≥ 3,600 images total
- [ ] ≥ 100 positive and ≥ 100 negative per category
- [ ] Annotation kappa ≥ 0.85 (dataset level)
- [ ] All categories per-kappa ≥ 0.80
- [ ] Image quality filters passed
- [ ] De-identification verified (sample audit of 5% of images)
- [ ] COCO JSON exports validated (schema check, no null bboxes)
- [ ] Test set sealed and dual-authorized
- [ ] CVC sign-off received
