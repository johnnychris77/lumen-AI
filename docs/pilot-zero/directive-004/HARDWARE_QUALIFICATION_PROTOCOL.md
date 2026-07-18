# LPZ-DIR-004 — Hardware Qualification Protocol (IQ / OQ / PQ)

**Purpose:** the protocol that qualifies laboratory equipment (borescope,
capture chain, workstation, storage/backup) before any image acquisition. No
device or workstation may be used for evidence capture until it has passed
**Installation Qualification (IQ)**, **Operational Qualification (OQ)**, and
**Performance Qualification (PQ)**, with results recorded.

This protocol is written to be executed on a **loaner or evaluation unit**;
passing qualification is a precondition of any purchase recommendation, not a
consequence of it.

## Definitions

* **IQ** — the equipment is installed and configured correctly, per spec.
* **OQ** — the equipment operates within its documented tolerances across its
  intended range.
* **PQ** — the equipment, operated by trained staff under the SOPs, repeatably
  produces evidence meeting acceptance criteria.

## General rules

* Each test records: item under test (serial/version), method, expected result,
  observed result, PASS/FAIL, operator, date.
* **Any FAIL blocks progression** to the next stage until resolved and re-tested.
* Environmental conditions (per `LAB_ENVIRONMENT_STANDARD.md`) are recorded at
  test time.

## Installation Qualification (IQ)

| ID | Test | Expected | Pass/Fail |
|---|---|---|---|
| IQ-1 | Borescope + probe are the specified/qualified units | Serials match records | |
| IQ-2 | Capture chain connects to the workstation; images transfer | Original-quality images land on the working tier | |
| IQ-3 | Workstation meets spec (`IMAGE_ACQUISITION_WORKSTATION.md`) | Meets minimums; versions recorded | |
| IQ-4 | Fixed mount / staging jig installed; geometry set | Documented, reproducible geometry | |
| IQ-5 | Isolated network, NTP, UPS present and healthy | All confirmed | |
| IQ-6 | Storage, secure volume, archive, backup target writable | All confirmed | |
| IQ-7 | Calibration references present and undamaged | All present with IDs | |

## Operational Qualification (OQ)

| ID | Test | Expected | Pass/Fail |
|---|---|---|---|
| OQ-1 | Focus across working field | Meets focus acceptance (`CALIBRATION_STANDARD.md`) | |
| OQ-2 | Illumination range & uniformity | Within exposure/uniformity tolerance | |
| OQ-3 | White-balance lock & stability | Neutral within tolerance; no drift | |
| OQ-4 | Color reference | Patch deltas within tolerance | |
| OQ-5 | Resolution | Meets/exceeds resolution floor | |
| OQ-6 | Scale reference at fixed geometry | Pixels-per-unit within tolerance | |
| OQ-7 | Metadata capture | Required provenance fields present; **no PHI-capable field forced** | |
| OQ-8 | Integrity hashing on ingest | Hash recorded and re-verifiable | |
| OQ-9 | Set the qualified tolerance numbers | Tolerance table in `CALIBRATION_STANDARD.md` filled and approved | |

## Performance Qualification (PQ)

| ID | Test | Expected | Pass/Fail |
|---|---|---|---|
| PQ-1 | **Repeatability run** — image a reference N times under SOPs | Cross-repeat variation within repeatability tolerance | |
| PQ-2 | **Operator repeatability** — two trained operators capture the same target | Results comparable within tolerance | |
| PQ-3 | **End-to-end evidence run** — register → calibrate → capture → review → store → archive → backup on sample instruments | Every image has complete provenance + valid hash; rejects quarantined | |
| PQ-4 | **Restore test** — restore evidence from backup | Restored evidence matches hashes | |
| PQ-5 | **Fail-closed check** — attempt capture with missing identity / failed calibration | System/SOP blocks the capture | |

## Acceptance criteria (summary)

Equipment is **qualified** only when **all** IQ, OQ, and PQ tests PASS and the
calibration tolerance table is approved. Partial passes do not qualify.

## Failure & retest procedure

1. Record the failure as an incident (SOP-10) with the failing test ID.
2. Determine root cause; apply corrective action.
3. **Re-run the failed test and any test its fix could affect.** A fix to
   geometry, firmware, or configuration invalidates prior OQ/PQ results for the
   affected checks, which must be repeated.
4. Only a fully re-passed protocol qualifies the equipment.

## Re-qualification triggers

Re-run the relevant IQ/OQ/PQ steps after: hardware/firmware change; probe
replacement; mount/geometry change; workstation OS/software change affecting
capture; relocation; or a repeatability drift observed in routine calibration.

## Records

All qualification records are archived as evidence and referenced by the
`LAB_READINESS_CHECKLIST.md` and `DIRECTIVE_004_REPORT.md`.
