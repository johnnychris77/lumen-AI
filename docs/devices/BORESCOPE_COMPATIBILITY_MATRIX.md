# Borescope & Camera Compatibility Matrix

Internal compatibility evidence for vendor-neutral image acquisition. LumenAI is
**designed for vendor-neutral borescope image acquisition** — it integrates with
the *image source*, not with any manufacturer's workflow. Any device that
presents to the OS/browser as a standard video input appears automatically as a
selectable camera source; file upload is always available as a fallback.

> **This is internal compatibility evidence, not certification.** Do not publish
> as manufacturer certification, endorsement, or partnership. Only claim specific
> device compatibility after the device reaches **Workflow Verified** below, and
> use vendor-neutral language ("designed to work with compatible borescope and
> camera sources").

## Compatibility tiers (how a device connects)

| Tier | Description | LumenAI handling |
|------|-------------|------------------|
| **1 — Browser video device** | Appears as a standard camera (UVC, etc.) | Live capture via MediaDevices; the default `MediaDevicesAdapter`. |
| **2 — File-based** | Device's own software saves image files | First-class **Upload / Drag & Drop** into the active workflow. Not inferior. |
| **3 — Vendor SDK / bridge** | Needs a proprietary SDK / native driver / local bridge | Implement the `BorescopeAdapter` interface — **no** workflow change. Only if an SDK is actually available. |
| **4 — Capture hardware** | HDMI / USB capture card / video adapter | If it presents as a standard camera, treated as Tier 1. |

## Status legend

`Untested` · `Detected` · `Basic Capture Verified` · `Workflow Verified` ·
`Limited Compatibility` · `Requires Adapter` · `Not Compatible`

## Registry

| Manufacturer | Model | Connection | OS | Browser | Detection | Preview | Capture | Resolution | Workflow attach | Known limitations | Test date | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Healthmark *(Test Device #1)* | *(TBD)* | USB / UVC | — | — | ⏳ | ⏳ | ⏳ | — | ⏳ | Pending hardware run | — | **Untested** |
| *Generic USB borescope* | *(any)* | USB / UVC | — | — | — | — | — | — | — | Expected Tier 1 | — | Untested |
| *Generic USB inspection camera* | *(any)* | USB / UVC | — | — | — | — | — | — | — | Expected Tier 1 | — | Untested |
| *HDMI/USB capture card* | *(any)* | Capture card | — | — | — | — | — | — | — | Expected Tier 1 if it presents as a camera | — | Untested |
| *File-based device* | *(any)* | Device software → file | — | — | n/a | n/a | via export | — | via Upload | Tier 2 — always supported | — | Untested |

Add one row per device tested. Record the fields above; keep the file internal.

## How a new device is added (the DoD)

Supporting a second standards-compatible USB borescope requires **none** of:
another inspection workflow, another upload workflow, another evidence model, or
manufacturer-specific business logic. A newly connected standards-compatible
borescope simply appears as another **Camera source** in the existing capture
panel. Only a genuinely proprietary (Tier 3) device needs new code — a new
`BorescopeAdapter` implementation — and even then the inspection/baseline/
evidence workflow is untouched.

## Architecture references

- `frontend/src/lib/imageAcquisition.ts` — vendor-neutral core (types, discovery,
  preference, capability detection, `BorescopeAdapter` interface,
  `ImageAcquisitionResult`).
- `frontend/src/lib/borescopeAdapter.ts` — default `MediaDevicesAdapter` (Tier 1/2/4).
- `frontend/src/components/ui/borescope-capture.tsx` — live capture UI.
- `docs/architecture/IMAGE_ACQUISITION_DECISION.md` — architecture decision.
- `docs/pilot/HEALTHMARK_BORESCOPE_TEST_PLAN.md` — Test Device #1 procedure.
