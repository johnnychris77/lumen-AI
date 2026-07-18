# LPZ-DIR-004 — Borescope Hardware Requirements

**Directive:** LPZ-DIR-004 — Hardware Qualification & Pilot Zero Laboratory
**Status:** Specification (vendor-neutral). No purchase is authorized until the
qualification framework (`HARDWARE_QUALIFICATION_PROTOCOL.md`) and the
evaluation scorecard (`BORESCOPE_SELECTION_SCORECARD.md`) are complete and
approved.

## Scope & non-goals

This document specifies the **minimum** capabilities a borescope (and its
capture chain) must provide to generate governed image evidence for **future**
computer-vision development in the Pilot Zero Laboratory.

* This is an **engineering laboratory** specification, not a clinical or
  hospital-deployment specification.
* It makes **no** clinical claim, **no** diagnostic claim, and **no** claim of
  FDA clearance or of compliance with HIPAA, SOC 2, ISO 13485, IEC 62304,
  ISO 14971, or 21 CFR Part 11.
* The images produced here are research/engineering evidence for dataset
  construction. No AI capability is added by this directive.

## Requirement priority levels

* **MUST** — mandatory; a device failing any MUST is disqualified.
* **SHOULD** — strongly preferred; weighted in the scorecard.
* **MAY** — optional/nice-to-have.

## 1. Optical & imaging requirements

| # | Attribute | Requirement | Level | Rationale / acceptance basis |
|---|---|---|---|---|
| 1 | Still image resolution | ≥ 1920×1080 native sensor pixels; no upscaled "interpolated" resolution counted | MUST | Sufficient spatial detail for future CV; measured against a resolution target (`CALIBRATION_STANDARD.md`). |
| 2 | Video resolution | ≥ 1920×1080 at ≥ 30 fps | SHOULD | Supports future motion/sequence capture; not required for still datasets. |
| 3 | Field of view (FOV) | Documented, ≥ 90° diagonal (direct-view); value must be stated by vendor | MUST | Needed to compute scale/coverage; unknown FOV is disqualifying. |
| 4 | Depth of field (DoF) | Documented working range that keeps a target instrument surface in acceptable focus at the intended standoff distance | MUST | Repeatable focus is an acceptance gate. |
| 5 | Focus | Fixed-focus with a documented in-focus range, OR controllable focus with repeatable detents | MUST | Auto-focus that "hunts" between captures is a rejection criterion unless it can be locked. |
| 6 | Illumination | Integrated, adjustable-intensity light source; stable color temperature across the intensity range used | MUST | Lighting stability is verified during calibration. |
| 7 | White balance | Manual/lockable white balance, OR a documented fixed white balance | MUST | Auto-white-balance that shifts per frame is disqualifying unless lockable. |
| 8 | Color fidelity | Able to image a color reference card with documented, repeatable color values | SHOULD | Basis for the color-reference check. |

## 2. Mechanical / probe requirements

| # | Attribute | Requirement | Level |
|---|---|---|---|
| 9 | Probe diameter | Documented; small enough to image the target instrument lumens/surfaces in scope for Pilot Zero | MUST |
| 10 | Working length | Documented; adequate to reach the intended imaging targets on the bench | MUST |
| 11 | Articulation | Articulation range documented (if articulating). Non-articulating probes are acceptable for bench targets | SHOULD |
| 12 | Durability | Documented probe bend-radius / cycle life; ruggedized connector | SHOULD |
| 13 | Sterility considerations | For laboratory bench use, sterility is **not** required; a documented cleaning/wipe-down procedure for the probe is required. No patient contact occurs in this lab | MUST |

> Note: Pilot Zero is a **laboratory** environment imaging instruments on a
> bench. No sterilization/patient-contact requirement applies; a probe cleaning
> procedure is documented in `LAB_ENVIRONMENT_STANDARD.md`.

## 3. Data, export & metadata requirements

| # | Attribute | Requirement | Level |
|---|---|---|---|
| 14 | Image export | Lossless or visually-lossless still export (e.g., PNG or high-quality/uncompressed formats). Heavily-compressed-only export is disqualifying | MUST |
| 15 | Video export | Standard container/codec export if video is used | SHOULD |
| 16 | Metadata availability | Device must expose capture metadata (timestamp; device/probe identifier or serial; capture settings where available). **No PHI shall ever be embedded in image metadata** | MUST |
| 17 | SDK / API availability | Documented SDK/API or an open export path (removable media, USB mass storage, or network export) so images can be ingested by the acquisition workstation without a proprietary black box | SHOULD |
| 18 | Storage | On-device storage and/or direct-to-host capture; capacity documented | MUST |
| 19 | Connectivity | USB and/or Ethernet/Wi-Fi export path documented. Wireless export, if used, must be on the isolated lab network (`LAB_ENVIRONMENT_STANDARD.md`) | MUST |

## 4. Power, support & lifecycle requirements

| # | Attribute | Requirement | Level |
|---|---|---|---|
| 20 | Battery | If battery-powered, documented runtime ≥ one acquisition session; mains operation supported for bench use | SHOULD |
| 21 | Regulatory status | Vendor to state device regulatory status **for reference only**. LumenAI makes no regulatory claim; laboratory use is non-clinical | MAY |
| 22 | Vendor support | Documented support channel and response expectation | SHOULD |
| 23 | Replacement parts | Availability of replacement probes/tips documented | SHOULD |
| 24 | Warranty | Documented warranty term | SHOULD |

## 5. Disqualifying conditions (automatic reject)

A candidate device is rejected regardless of score if any of the following hold:

1. Undocumented or non-repeatable FOV, focus range, or white balance.
2. Export path is proprietary-only with **no** way to obtain original-quality
   images for ingestion.
3. Metadata cannot be captured, or the device forces embedding of any field
   that could carry PHI.
4. No mechanism to lock/stabilize exposure, focus, or white balance for
   repeatable captures.

## 6. Traceability

Every device evaluated against this specification is scored in
`BORESCOPE_SELECTION_SCORECARD.md` and qualified via
`HARDWARE_QUALIFICATION_PROTOCOL.md`. A device may enter Pilot Zero image
acquisition **only** after passing IQ/OQ/PQ and being recorded on the
`LAB_READINESS_CHECKLIST.md`.
