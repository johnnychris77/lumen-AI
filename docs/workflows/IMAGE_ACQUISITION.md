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
| `BorescopeCapturePanel` | `frontend/src/components/ui/borescope-capture.tsx` | Live borescope/webcam capture UI: device selection, preference memory, capability-driven controls. Emits JPEG `File`s + `ImageAcquisitionResult`. |
| Vendor-neutral core | `frontend/src/lib/imageAcquisition.ts` | Pure, DOM-free: types (`ImageAcquisitionResult`, `SourceType`, `DeviceType`), discovery, preference resolution, capability detection, `BorescopeAdapter` interface. Unit-tested. |
| `MediaDevicesAdapter` | `frontend/src/lib/borescopeAdapter.ts` | Default adapter (Tier 1/2/4) binding the core to `navigator.mediaDevices` + `localStorage`. |
| `imageAcquisitionSource(file)` | (exported from `image-acquisition.tsx`) | Recovers `borescope_capture` \| `file_upload` from a file (backend `image_source` vocabulary). |

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

## Vendor neutrality

LumenAI integrates with the **image source**, never with a borescope
manufacturer's workflow. Any device that presents as a standard video input — a
Healthmark borescope, any third-party USB borescope, an industrial inspection
camera, an HDMI/USB capture card, or a webcam — appears automatically as a
selectable **Camera source** and produces the same `ImageAcquisitionResult`.
There is no hard-coded manufacturer name, USB VID/PID, or device label, and no
device-specific workflow. Adding a second standards-compatible borescope needs no
code; a proprietary (Tier 3) device is added by implementing the `BorescopeAdapter`
interface without changing the inspection/baseline/evidence workflow. See
`docs/architecture/IMAGE_ACQUISITION_DECISION.md` and
`docs/devices/BORESCOPE_COMPATIBILITY_MATRIX.md`.

## The standard result object

Every source produces an `ImageAcquisitionResult`:
`{ image, sourceType, captureTimestamp, deviceType?, deviceLabel?, captureMethod, metadata? }`.
`sourceType` is generic (`borescope | camera | file_upload | external_capture`).
Device `metadata` (manufacturer/model/label/driver) is **optional** — populated
only when a source actually provides it (standard web APIs expose only a label).

## Device preference & capabilities

- **Preference memory** — the chosen camera source is remembered (by id *and*
  label) in `localStorage`; if it disappears (e.g. unplugged, id regenerated) the
  panel falls back to the selector. The first camera is never assumed to be the
  borescope.
- **Capability-driven controls** — optional torch/zoom controls appear only when
  the device reports supporting them (`track.getCapabilities()`); basic capture
  always works without them.

## Tests

`frontend/tests/imageAcquisition.test.mts` (run `npm test` — Node's built-in
runner, no test-framework dependency) covers the 13 device scenarios with a
mocked MediaDevices set plus the pure vendor-neutral logic: single/multi camera,
device appearing after load, permission denied/granted, device removed
mid-preview, preferred-device resolution + label fallback, unsupported browser,
file-upload fallback, capture failure, consecutive captures, generic
classification (a bare brand name is not a borescope), and capability detection.
