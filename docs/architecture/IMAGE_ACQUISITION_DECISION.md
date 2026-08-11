# Architecture Decision — Image Acquisition Everywhere

**Status:** Accepted · **Sprint:** Image Acquisition Everywhere (v1.0) ·
**Scope:** UX refactor only — core architecture, inspection logic, AI
specialists, and evidence governance are unchanged.

## Context

Borescope capture previously behaved as its own **standalone workflow**: a
dedicated "Borescope Capture" page (`/inspection/capture`, `CapturePage.tsx`)
reached from the main "Inspection Intelligence" navigation. A technician who was
in the middle of a New Inspection had to leave that workflow, go to the capture
page, capture-and-analyze there, and navigate back. Meanwhile the actual
image-attach surfaces (New Inspection, Inspection Image Upload, baseline uploads)
only offered plain file inputs / dropzones.

The borescope is not a workflow. It is an **image acquisition source**, exactly
like a webcam, a file picker, or drag-and-drop. The active workflow should own
the image; the borescope should only provide it.

## Decision

Introduce one reusable image-source layer and embed it wherever LumenAI needs an
image, so the borescope is available inline as a source with **no context
switch**.

1. **`BorescopeCapturePanel`** (`components/ui/borescope-capture.tsx`) — the
   live-capture engine, extracted from the old standalone page. Uses the
   standard `navigator.mediaDevices.getUserMedia` / `enumerateDevices` web APIs,
   so any UVC-class device (the Healthmark borescope, a USB video grabber, a
   laptop webcam, an external camera) is a selectable video input. Emits captured
   frames as JPEG `File` objects. Handles permission-denied, no-device,
   device-in-use, over-constrained, and unsupported-browser states with plain
   language — never a raw JS error.

2. **`ImageAcquisition`** (`components/ui/image-acquisition.tsx`) — the
   **"Add Image" source picker**: *Capture from Borescope* · *Upload Existing
   Image* · *Drag & Drop*. It is intentionally **controlled** (`files` /
   `onChange`) and **network-free** — it produces `File` objects only and never
   calls an endpoint.

### Key principle — the workflow owns the image

`ImageAcquisition` does **not** upload. The parent workflow keeps using its
existing, governed upload endpoint (`POST /api/inspections/upload-images` for
inspections; the vendor-baseline image endpoint for baselines). Because the
borescope frame is just another `File` handed to the same code path, **every
governance control is preserved with zero new code**: authorization
(`require_inspection_runner`), the read-only viewer rule, tenant scoping,
content-type allow-list (`jpeg/png/webp`), the 10 MB cap, EXIF stripping,
SHA-256 hashing, audit logging, and retention. There is deliberately **no second
upload path** to weaken.

## Data flow

```
Click "Add Image"
  → choose source (Borescope | Upload | Drag&Drop)   [ImageAcquisition]
  → Borescope: live preview → capture → confirm       [BorescopeCapturePanel]
    Upload/Drop: pick file(s)
  → File objects handed to the ACTIVE workflow (state)
  → workflow submits via its existing governed endpoint
      POST /api/inspections/upload-images?image_source=…
  → server: authz + tenant + type/size + EXIF strip + SHA-256 + audit
  → image attached to the current inspection / baseline record
  → user continues exactly where they were
```

## Source provenance (additive, no schema change)

Borescope frames are minted with a stable filename prefix
(`borescope-capture-…jpg`); `imageAcquisitionSource(file)` recovers
`borescope_capture` vs `file_upload` from it. Workflows pass an aggregate
`image_source` (`borescope_capture` | `file_upload` | `mixed`) as a **query
parameter** to the existing upload endpoint. The server records it in the
per-image response and the audit `details`, validated against a fixed
allow-list (unknown values are ignored). **No database migration** — this is
audit/response metadata only, layered on the endpoint's already-extensible
`details` dict.

## Standalone page decision

The old page is **repositioned, not deleted**, because it still provides genuine
device-diagnostics / compatibility-test value (verify a camera source, run an
end-to-end capture on a non-clinical test instrument — the home-lab pilot
scenario). It is:

- retitled **"Borescope Diagnostics & Device Test"**,
- **removed** from the "Inspection Intelligence" (technician) navigation,
- **moved** under **Administration** (elevated roles only),
- annotated with a pointer to the embedded "Add Image → Capture from Borescope"
  flow for routine work.

Route (`/inspection/capture`) is retained so existing links and the shared
`/station` kiosk are unaffected.

## Vendor-neutral device model

LumenAI is **designed for vendor-neutral borescope image acquisition** — it
integrates with the image *source*, never with a manufacturer's workflow. There
is no hard-coded manufacturer name, USB VID/PID, or device label anywhere, and no
device-specific business logic or workflow.

```
ANY COMPATIBLE BORESCOPE
   → DEVICE / CAPTURE ADAPTER          (BorescopeAdapter)
   → UNIFIED IMAGE ACQUISITION         (ImageAcquisition / BorescopeCapturePanel)
   → STANDARD LUMENAI IMAGE OBJECT     (ImageAcquisitionResult)
   → INSPECTION / BASELINE / EVIDENCE WORKFLOW
```

**Compatibility tiers** (see `docs/devices/BORESCOPE_COMPATIBILITY_MATRIX.md`):
Tier 1 browser video devices (UVC cameras/borescopes) via MediaDevices; Tier 2
file-based devices via first-class Upload/Drag&Drop; Tier 3 proprietary-SDK
devices via a future `BorescopeAdapter` implementation (no workflow change);
Tier 4 HDMI/USB capture hardware treated as Tier 1 when it presents as a camera.

**Core module** `frontend/src/lib/imageAcquisition.ts` (pure, DOM-free, unit-tested):
- `ImageAcquisitionResult` — the one standard object every source produces:
  `{ image, sourceType, captureTimestamp, deviceType?, deviceLabel?, captureMethod, metadata? }`.
  `sourceType` is generic (`borescope | camera | file_upload | external_capture`) —
  never a vendor value; device manufacturer/model/label/driver metadata is
  **optional**, populated only when a source actually provides it.
- Generic device classification from OS labels using only industry-generic
  descriptor words (borescope/capture/usb/integrated/virtual) — a display hint
  only, never authoritative, never manufacturer-specific.
- Injectable discovery (`listVideoInputs`, `requestVideoAccess`) over a
  `MediaDevices`-like surface, so the 13 device scenarios are unit-tested with a
  fake device set (`frontend/tests/imageAcquisition.test.mts`, `npm test` — Node's
  built-in runner, no test-framework dependency).
- Device-preference memory (`resolvePreferredDevice` + localStorage): remembers
  the chosen source by id **and** label, falls back to selection if it disappears,
  and never assumes the first camera is the borescope.
- Capability detection (`supportedOptionalControls`): optional torch/zoom controls
  are exposed only when the device reports them; basic capture always works without.

**Adapter interface** `BorescopeAdapter` + default `MediaDevicesAdapter`
(`frontend/src/lib/borescopeAdapter.ts`): isolates *how* frames are acquired from
the workflow that consumes them. Adding a second standard USB borescope requires
no code — it appears as another camera source. Only a Tier-3 proprietary device
needs a new adapter, and even then the inspection/baseline/evidence workflow is
untouched. Healthmark is **Test Device #1**, not the architecture.

## Alternatives considered

- **Make the component upload directly.** Rejected — it would create a second
  upload path and duplicate the governance logic the backend already owns.
- **Add a `capture_source` DB column.** Rejected as unnecessary for this sprint;
  provenance as audit/response metadata is sufficient and non-breaking. A schema
  field can be added later if source-level querying is required.
- **Delete the standalone page.** Rejected — it retains diagnostic value.

## Consequences

- Technicians never leave the active workflow to use the borescope.
- One acquisition layer to maintain; consistent UX across inspection and
  baseline surfaces; consistent device-error handling and accessibility.
- Governance, authorization, and baseline-approval semantics are untouched.
