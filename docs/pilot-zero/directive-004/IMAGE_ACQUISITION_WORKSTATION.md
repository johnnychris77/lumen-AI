# LPZ-DIR-004 — Image Acquisition Workstation Specification

**Purpose:** define the workstation that captures, reviews, and hands off
governed image evidence in the Pilot Zero Laboratory. Vendor-neutral; states
capabilities and acceptance criteria, not brands.

## 1. Computer

| Attribute | Minimum | Preferred | Acceptance basis |
|---|---|---|---|
| CPU | Modern 6-core class | 8+ core | Runs capture + review software without frame drops |
| RAM | 16 GB | 32 GB | Handles large image buffers and review software |
| GPU | Integrated acceptable for capture/review | Discrete (future dataset tooling) | Not required for acquisition; noted for future use only |
| OS | Vendor-supported, patched, on the isolated lab network | — | Security per `LAB_ENVIRONMENT_STANDARD.md` |
| Ports | USB 3.x for capture; wired Ethernet | + capture card if device requires | Matches selected borescope export path |

## 2. Storage

| Tier | Requirement |
|---|---|
| Working (local) | Fast SSD for the active session; sized for a full day of captures with headroom |
| Secure storage | Access-controlled volume; integrity hash recorded per image on ingest |
| Archive | Write-once/append-only archive of accepted evidence (Zone 10) |
| Backup | Independent copy on separate media/host; restore-tested (Zone 11) |

Storage integrity: every accepted image is hashed (e.g., SHA-256) at ingest and
the hash is stored with its provenance record so tampering/corruption is
detectable. No image is promoted to a dataset without a matching hash.

## 3. Backup strategy

* **3-2-1 principle:** ≥ 3 copies, on ≥ 2 media types, with ≥ 1 off the primary
  host/location.
* Backups scheduled and logged; a **restore test** is performed and recorded on
  the `LAB_READINESS_CHECKLIST.md` and periodically thereafter.
* Backup contains evidence + provenance metadata; contains **no PHI** (there is
  none in this lab).

## 4. Power protection (UPS)

* Workstation, display, illumination, and any capture appliance on a UPS sized
  for graceful shutdown (protects an in-flight capture/write).
* UPS runtime documented; self-test scheduled; battery replacement tracked.

## 5. Networking

* **Isolated lab network** (segmented / no general internet exposure); only the
  hosts required for capture, storage, and backup are attached.
* Remote/cloud sync, if any, is an explicit, reviewed exception — default is
  local-only.
* Time synchronization (NTP) so every capture timestamp is trustworthy and
  comparable.

## 6. Display & display calibration

| Attribute | Requirement |
|---|---|
| Monitor resolution | ≥ 1920×1080; sized to review full-resolution captures 1:1 |
| Color | Display calibrated to a documented target (white point, gamma, luminance) |
| Calibration cadence | Verified at lab startup per `CALIBRATION_STANDARD.md`; recalibrated on schedule or after any hardware change |
| Ambient | Controlled, non-glare lighting at the review position |

## 7. Capture geometry & mounting

* **Fixed camera/probe mount** and an instrument staging jig so standoff
  distance and angle are repeatable across sessions.
* Documented, reproducible geometry is a prerequisite for the repeatability
  acceptance test (`CALIBRATION_STANDARD.md`, `HARDWARE_QUALIFICATION_PROTOCOL.md`).

## 8. Lighting at the station

* Calibrated, adjustable illumination with stable color temperature; settings
  recorded per session.
* Ambient light controlled so it does not contaminate captures (see
  `LAB_ENVIRONMENT_STANDARD.md`).

## 9. Instrument identification

* **Barcode/QR scanner** for reading instrument identity (barcode/QR/UDI).
* Manual-entry fallback with a dual-check to prevent mis-identification.
* The instrument identity is bound to the capture session **before** the first
  image is taken (fail-closed: no identity → no capture).

## 10. Image review software

* Displays captures at full native resolution (1:1) with zoom/pan.
* Shows the provenance record alongside the image (instrument ID, device,
  operator, timestamp, calibration status).
* Provides an **accept / reject-quarantine** action that is recorded.
* Does **not** alter original pixels; any enhancement is a non-destructive view
  only, and the original is preserved as the evidence of record.

## 11. Software integrity & governance

* All capture/review software versions recorded (reproducibility).
* No AI/inference capability is introduced by this workstation; it captures and
  reviews evidence only. Any future model tooling is out of scope for
  Directive 004.

## Acceptance

The workstation is accepted only after the Installation and Operational
Qualification steps in `HARDWARE_QUALIFICATION_PROTOCOL.md` pass and the
relevant `LAB_READINESS_CHECKLIST.md` items are signed.
