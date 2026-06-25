# Pilot Image Ingestion Guide

This guide describes how to add real instrument photographs to the LumenAI Demo Image Library for pilot program use.

---

## Folder Structure

Place images in the following directory (served by Vite as static assets):

```
frontend/public/demo-images/lumened-instruments/
  {facility}_{instrument}_{model}_{identifier}_{imageType}_{findingCategory}_{YYYYMMDD}.jpg
```

**Subfolders are not required.** All pilot images live flat in `lumened-instruments/`.

---

## Naming Convention

```
{facilitySlug}_{instrumentSlug}_{modelSlug}_{identifier}_{imageType}_{findingCategory}_{YYYYMMDD}.jpg
```

| Segment | Description | Example |
|---------|-------------|---------|
| `facilitySlug` | Facility short name, lowercase, underscores | `bon_secours`, `mercy_health` |
| `instrumentSlug` | Instrument type, lowercase, underscores | `flexible_ureteroscope`, `laparoscope` |
| `modelSlug` | Manufacturer model identifier | `olympus_v2` |
| `identifier` | Instrument barcode, QR, UDI, or KeyDot ID | `BS_12345` |
| `imageType` | One of: `baseline`, `inspection`, `borescope`, `finding` | `baseline` |
| `findingCategory` | One of: `blood`, `bone`, `tissue`, `debris`, `corrosion`, `crack`, `insulation_damage`, `other`, `none` | `none` |
| `YYYYMMDD` | Image capture date | `20240115` |

**Example:**
```
bon_secours_flexible_ureteroscope_olympus_v2_BS_12345_baseline_none_20240115.jpg
```

---

## Metadata Schema

Each image in the manifest (`frontend/src/data/pilotImageManifest.ts`) carries this metadata:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique image ID (matches filename without `.jpg`) |
| `facilityName` | string | Human-readable facility name |
| `facilityId` | string | Facility slug |
| `instrumentName` | string | Human-readable instrument type |
| `manufacturer` | string | Device manufacturer name |
| `model` | string | Device model name |
| `barcode` | string | Facility barcode / asset tag |
| `qrCode` | string \| undefined | QR code value if present |
| `udi` | string \| undefined | FDA UDI if present |
| `keyDot` | string \| undefined | KeyDot ID if present |
| `imageType` | `baseline` \| `inspection` \| `borescope` \| `finding` | Image category |
| `findingCategory` | string | Finding type or `"none"` |
| `captureDate` | string | ISO date of image capture |
| `baselineStatus` | `approved` \| `pending` \| `rejected` \| undefined | Baseline review status |
| `riskLevel` | `low` \| `medium` \| `high` \| `critical` \| undefined | Risk level for finding images |
| `available` | boolean | Whether the actual image file exists |
| `imageSrc` | string | Path relative to `/public` (used as `<img src>`) |
| `placeholderSrc` | string | Fallback SVG path if `available === false` or image 404s |

---

## Workflow to Add a Real Image

1. **Capture the photograph** using a compliant device (camera, borescope output, etc.).

2. **Name the file** according to the naming convention above.

3. **Copy the file** to `frontend/public/demo-images/lumened-instruments/`.

4. **Update the manifest** in `frontend/src/data/pilotImageManifest.ts`:
   - Set `available: true` for the matching entry.
   - Confirm `imageSrc` matches the filename exactly (case-sensitive on Linux).

5. **Verify** by running the frontend dev server (`npm --prefix frontend run dev`) and visiting `/demo-image-library`. The image should appear with no placeholder fallback.

6. **Commit** the image file and updated manifest together.

---

## PHI Avoidance Requirements

**Do not include any of the following in image files or filenames:**

- Patient names, dates of birth, MRN, or any patient identifiers
- Procedure scheduling information linked to a specific patient
- OR / room labels that could identify a patient encounter
- Protected Health Information as defined by HIPAA 45 CFR § 164.514

**Permitted metadata (de-identified):**

- Instrument asset tag / barcode (facility property, not patient data)
- Manufacturer / model / UDI (public device information)
- Capture date (date of inspection, not procedure date)
- Finding category (equipment state, not patient outcome)

If you are unsure whether an image contains PHI, consult your facility Privacy Officer before ingestion.

---

## Image Quality Requirements

| Parameter | Requirement |
|-----------|-------------|
| Format | JPEG (`.jpg`) preferred; PNG accepted |
| Resolution | Minimum 800 × 600 px |
| File size | Maximum 10 MB per image |
| Color space | sRGB |
| Orientation | Landscape preferred for consistency |

---

## Batch Import

To add multiple images at once:

1. Prepare all image files with correct names.
2. Copy all files to `frontend/public/demo-images/lumened-instruments/`.
3. Update the manifest: change `available: false` → `available: true` for each entry.
4. If adding new instruments not in the manifest, add a new entry following the `PilotImage` type definition.
5. Run `npm --prefix frontend run build` to confirm no TypeScript errors.
6. Commit and push.

---

## Validation Checklist

- [ ] Filename matches the naming convention exactly
- [ ] File exists in `frontend/public/demo-images/lumened-instruments/`
- [ ] Manifest entry has `available: true`
- [ ] `imageSrc` path matches the filename (case-sensitive)
- [ ] No PHI in filename, EXIF metadata, or image content
- [ ] Image file size ≤ 10 MB
- [ ] `npm --prefix frontend run build` passes without errors
- [ ] Image displays correctly in Demo Image Library (`/demo-image-library`)
- [ ] Image displays correctly in Instrument Passport (Infrastructure → Instrument Passport tab)

---

## Placeholder Fallback

If `available: false` or the image file is missing at runtime, the UI automatically falls back to a typed SVG placeholder:

| Image Type | Placeholder | Color |
|------------|-------------|-------|
| `baseline` | `_placeholder-baseline.svg` | Blue |
| `inspection` | `_placeholder-inspection.svg` | Slate |
| `borescope` | `_placeholder-borescope.svg` | Purple |
| `finding` | `_placeholder-finding.svg` | Red |

The fallback is handled by `<img onError>` in `DemoImageLibraryPage.tsx` and `GlobalInfrastructureConsole.tsx`. No manual intervention is needed — the build never breaks due to a missing image.

---

*LumenAI Pilot Program — Internal Use Only*
*Do not share externally without approval from the LumenAI Customer Success team.*
