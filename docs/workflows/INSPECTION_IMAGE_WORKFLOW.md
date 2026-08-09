# Inspection Image Workflow

How a technician attaches an inspection image — now with the borescope embedded
as an image source, no separate page.

## Flow

```
New Inspection
  → Instrument details
  → Inspection Images → Add Inspection Image
      ├─ Capture from Borescope   (live capture, inline)
      ├─ Upload Existing Image
      └─ Drag & Drop
  → image(s) attach to THIS inspection
  → Submit → AI baseline check → prediction → supervisor review if no baseline
```

The technician stays on the New Inspection form the whole time. Borescope
capture happens in an inline panel; on **Attach**, the frame becomes a `File` in
the form's image list, and submission proceeds exactly as before.

## Screens

- **`NewInspectionPage.tsx`** — the `Inspection Images` section renders
  `<ImageAcquisition label="Add Inspection Image" …>` for the required images and
  a second `<ImageAcquisition label="Add Borescope Image" …>` for the optional
  borescope set. Per-image view tagging (zone / view / quality / notes) and the
  coverage engine are unchanged and operate over the acquired files.
- **`InspectionImageUploadPage.tsx`** — the standalone bulk upload page now uses
  `<ImageAcquisition>` for both its inspection and borescope image sets.

## Backend path (unchanged, governed)

Both pages upload via `POST /api/inspections/upload-images`:

1. `require_inspection_runner` — operator / spd_manager / admin only; **viewers
   get a clear 403** ("Viewer access is read-only…").
2. Content-type must be `image/jpeg|png|webp`; empty → 422; > 10 MB → 413.
3. Tenant is derived server-side from request context and stamped on every image
   record — the client cannot place a frame under an arbitrary tenant.
4. Each frame is EXIF-processed (per retention config), SHA-256 hashed,
   identifier-decoded (barcode/QR/UDI via pyzbar when available), and audit
   logged (`inspection_image_uploaded`).
5. **New:** an optional `image_source` query param
   (`borescope_capture` | `file_upload` | `mixed`) is recorded per image and in
   the audit `details`. Validated against a fixed allow-list; unknown values are
   ignored. No schema change.

## Result contract & safety (unchanged)

The honest, scope-limited result contract, placeholder-scoring disclosure,
baseline separation, and `human_review_required: true` behavior are untouched by
this sprint. Borescope-sourced images flow into exactly the same analysis and
disposition path as uploaded images.

## Tests

`backend/tests/test_image_acquisition_upload.py` pins the governance invariants
for the shared path: unauthenticated rejected, viewer 403, operator can attach a
borescope frame, provenance echoed, unknown source ignored, unsupported type
422, empty 422, oversized 413, tenant server-derived.
