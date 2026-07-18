# LPZ-DIR-004 — Laboratory Standard Operating Procedures (SOPs)

**Purpose:** the step-by-step procedures for operating the Pilot Zero
Laboratory (Directive 004, Phase 7). Each SOP has an owner role and produces a
logged record. Fail-closed: if a required step cannot be completed or verified,
stop and quarantine — do not capture or promote evidence.

## SOP-01 — Daily startup

1. Confirm environment within band (temp/humidity/lighting) — log readings.
2. Power up workstation, display, illumination, capture appliance; confirm UPS
   healthy.
3. Confirm time sync (NTP) and network isolation status.
4. Confirm storage, secure volume, and backup target are online and writable.
5. Record startup in the daily log (operator, timestamp).

## SOP-02 — Equipment inspection

1. Inspect probe/optics and staging jig for damage or soiling; clean per
   `LAB_ENVIRONMENT_STANDARD.md` §9.
2. Confirm the borescope and mount are the qualified units (serial matches the
   qualification record).
3. Any damage → quarantine the item and raise an incident (SOP-10); do not use.

## SOP-03 — Calibration verification

1. Run every check in `CALIBRATION_STANDARD.md` (focus, lighting, white balance,
   color, scale, resolution, repeatability).
2. Record results against the OQ tolerances.
3. **Any fail → do not proceed.** Correct and re-run, or quarantine the device.

## SOP-04 — Instrument registration

1. Read instrument identity (barcode/QR/UDI) with the scanner; on failure, use
   the dual-check manual entry.
2. Create/confirm the governed instrument record (unique lab instrument ID).
3. Record surface state/condition (engineering note) before imaging.
4. Bind the instrument identity to the capture session **before** any image.

## SOP-05 — Image capture

1. Confirm calibration status is PASS for the current session.
2. Place the instrument in the fixed jig at the qualified geometry.
3. Set/confirm locked focus, exposure, white balance; record settings.
4. Capture the required views; each image is written with provenance metadata
   (instrument ID, device/probe ID, operator, timestamp, calibration status).
   **No PHI** is entered anywhere.

## SOP-06 — Image verification (QC review)

1. A reviewer **other than the acquirer** opens each capture at 1:1.
2. Verify image quality (focus/exposure/WB/coverage) and **provenance
   completeness**.
3. **Accept** → image + provenance move to secure storage; integrity hash
   recorded. **Reject** → quarantine (re-capture or discard), logged with reason.

## SOP-07 — Shutdown

1. Confirm all accepted evidence is in secure storage and archived; run/confirm
   backup.
2. Close open sessions; ensure no orphaned captures remain in the working tier.
3. Power down per equipment guidance; secure the lab (physical security).
4. Record shutdown in the daily log.

## SOP-08 — Cleaning

1. Clean probe/optics and jig between instruments and at end of day per
   `LAB_ENVIRONMENT_STANDARD.md` §9.
2. Log cleaning (operator, timestamp, materials).

## SOP-09 — Maintenance

1. Track scheduled maintenance for borescope, workstation, UPS, and references
   (recalibration/replacement of references on schedule).
2. Any maintenance or hardware change → re-run the relevant IQ/OQ steps before
   resuming capture (`HARDWARE_QUALIFICATION_PROTOCOL.md`).

## SOP-10 — Incident reporting

1. Any deviation (calibration fail, damage, mis-identification, data-integrity
   or access anomaly) is recorded as an incident: what/when/who, impact on
   evidence, and containment.
2. Affected evidence is quarantined pending disposition.
3. Root cause and corrective action recorded; readiness re-evaluated if needed.

## Records & audit

Every SOP produces a dated, attributable log entry archived as evidence. These
logs are the operational basis for the `LAB_READINESS_CHECKLIST.md` and the
`DIRECTIVE_004_REPORT.md`.
