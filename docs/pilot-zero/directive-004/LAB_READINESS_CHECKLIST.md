# LPZ-DIR-004 — Laboratory Readiness Checklist

**Purpose:** the gate that must be satisfied and **approved** before **any**
image acquisition begins. No captures for dataset purposes may occur while any
mandatory item is open. This checklist is a governance control, not a formality.

**Rule:** No image acquisition may begin until this checklist is complete and
signed by the Lab Lead (and, per program governance, the directive approver).

## A. Hardware installed

- [ ] Borescope + probe are the qualified units (serials recorded) — IQ-1
- [ ] Capture chain transfers original-quality images — IQ-2
- [ ] Workstation meets spec; software versions recorded — IQ-3
- [ ] Fixed mount / staging jig installed; geometry documented — IQ-4
- [ ] Barcode/QR scanner installed and reading

## B. Calibration completed

- [ ] All calibration checks PASS (focus, lighting, WB, color, scale, resolution, repeatability) — OQ-1..6
- [ ] Calibration tolerance table filled and approved — OQ-9
- [ ] Calibration references present, undamaged, ID'd — IQ-7

## C. Workstation configured

- [ ] Display calibrated to documented target
- [ ] Review software shows 1:1 image + provenance; accept/reject-quarantine works
- [ ] Original pixels preserved (non-destructive review confirmed)
- [ ] Instrument-identity binding is enforced before capture (fail-closed) — PQ-5

## D. Storage validated

- [ ] Secure storage online, access-controlled
- [ ] Integrity hashing on ingest verified — OQ-8
- [ ] Write-once/append-only archive operational

## E. Backup validated

- [ ] 3-2-1 backup configured and scheduled
- [ ] **Restore test passed** — PQ-4
- [ ] Disaster-recovery drill performed and recorded

## F. Security validated

- [ ] Isolated network; NTP time sync confirmed
- [ ] UPS healthy; self-test recorded
- [ ] Physical security in place; removable media controlled
- [ ] Access control: individual accounts, least privilege, access list reviewed
- [ ] Separation of duties confirmed (reviewer ≠ acquirer)

## G. Documentation approved

- [ ] `BORESCOPE_HARDWARE_REQUIREMENTS.md` approved
- [ ] `BORESCOPE_SELECTION_SCORECARD.md` completed for the device in use
- [ ] `PILOT_ZERO_LAB_DESIGN.md`, `IMAGE_ACQUISITION_WORKSTATION.md`, `CALIBRATION_STANDARD.md`, `LAB_ENVIRONMENT_STANDARD.md`, `LAB_OPERATING_PROCEDURES.md` approved
- [ ] `HARDWARE_QUALIFICATION_PROTOCOL.md` executed; IQ/OQ/PQ all PASS
- [ ] End-to-end evidence run passed — PQ-3

## H. Personnel trained

- [ ] Intake operator trained on SOP-01..04, 08, 10
- [ ] Acquisition operator trained on SOP-01..05, 07..10
- [ ] Reviewer trained on SOP-06 and quarantine handling
- [ ] Lab Lead trained on storage/archive/backup/DR governance
- [ ] Training records archived

## I. Guardrails confirmed

- [ ] No PHI enters the lab, images, or metadata
- [ ] No clinical/diagnostic/regulatory claim; no compliance claim (HIPAA/SOC 2/ISO 13485/IEC 62304/ISO 14971/21 CFR Part 11)
- [ ] No AI/model capability introduced by the lab (evidence capture only)

## Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Lab Lead | | | |
| Directive Approver | | | |

**Readiness status:** ☐ NOT READY ☐ READY (all mandatory items complete & signed)

Until READY is signed, acquisition is prohibited.
