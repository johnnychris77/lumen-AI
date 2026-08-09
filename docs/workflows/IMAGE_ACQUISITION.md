# Image Acquisition — Reusable "Add Image" Layer

LumenAI has **one** way to attach an image, used everywhere an inspection or
baseline image is needed. The user clicks **Add Image**, chooses a **source**,
captures or uploads, and the image attaches to the record they are already on —
no context switching.

```
CLICK ADD IMAGE → CHOOSE SOURCE → CAPTURE OR UPLOAD → ATTACHED → CONTINUE
```

## Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `ImageAcquisition` | `frontend/src/components/ui/image-acquisition.tsx` | Source picker (Borescope / Upload / Drag&Drop) + previews. Controlled, network-free. |
| `BorescopeCapturePanel` | `frontend/src/components/ui/borescope-capture.tsx` | Live borescope/webcam capture via `getUserMedia`. Emits JPEG `File`s. |
| `imageAcquisitionSource(file)` | (exported from `image-acquisition.tsx`) | Recovers `borescope_capture` \| `file_upload` from a file. |

### `ImageAcquisition` props

| Prop | Default | Notes |
|------|---------|-------|
| `files` / `onChange` | — | **Controlled.** Parent owns the list of acquired `File`s. |
| `label` | `"Add Image"` | Contextual, e.g. `"Add Inspection Image"`, `"Add Baseline Image"`. |
| `multiple` | `true` | Single-image mode when `false`. |
| `maxFiles` | `10` | Cap on retained files. |
| `maxBytes` | `10 MB` | Matches the backend limit. |
| `disabled` | `false` | Read-only (e.g. viewer role / locked record). |
| `onEvent` | — | Optional non-PHI telemetry hook (`image_source_opened`, `borescope_capture_started/completed`, `file_upload_completed`, `camera_permission_denied`, `camera_unavailable`). |

The component **never uploads**. It produces `File` objects; the host workflow
uploads them through its existing, governed endpoint. This is what preserves
tenant isolation, authorization, EXIF stripping, SHA-256 hashing, audit, and
retention — there is no second, weaker path.

## Source provenance

Borescope frames are named `borescope-capture-<timestamp>.jpg`; uploads keep
their filename. Workflows derive an aggregate `image_source`
(`borescope_capture` | `file_upload` | `mixed`) and pass it to
`POST /api/inspections/upload-images?image_source=…`. The server echoes it per
image and records it in the audit trail, validated against a fixed allow-list.
No schema change.

## Device handling (borescope)

`BorescopeCapturePanel` surfaces clear, non-technical messages for: permission
denied, no camera found, device in use, over-constrained selection, and browsers
without camera support. It offers a **camera-source selector** when more than one
video input is present (built-in camera, Healthmark borescope, external camera —
enumerated safely by label, never by a hard-coded USB id). On unsupported
devices (e.g. some mobile webviews) it directs the user to file upload, which is
always available.

## Accessibility & responsive

- Keyboard-operable dropzone (`role="button"`, Enter/Space), visible focus,
  labeled controls, `aria-live` status region for camera state, `alt` text on
  previews, `role="alert"` on errors.
- Source options stack vertically on mobile with large touch targets; the live
  preview stays within the viewport; capture/confirm/cancel remain reachable.

## Where it is used

- **New Inspection** (`NewInspectionPage.tsx`) — inspection images + optional
  borescope images.
- **Inspection Image Upload** (`InspectionImageUploadPage.tsx`).
- **Baseline image upload** (`components/ui/baseline-image-upload.tsx`) — used by
  the baseline upload page, dashboard, instrument passport, and training center.

See `INSPECTION_IMAGE_WORKFLOW.md` and `BASELINE_IMAGE_WORKFLOW.md` for the
end-to-end flows.
