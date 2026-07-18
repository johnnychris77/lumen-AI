# LPZ-DIR-004 — Directive Report: Hardware Qualification & Pilot Zero Laboratory

## Executive summary

Directive 004 establishes the **engineering laboratory framework** for producing
governed, repeatable, traceable image evidence of surgical instruments for
**future** computer-vision development. It delivers a complete, vendor-neutral
specification set: hardware requirements, an evidence-based selection scorecard,
laboratory design, workstation spec, calibration standard, environmental
standard, SOPs, an IQ/OQ/PQ qualification protocol, and a readiness checklist.

This directive is **documentation and framework only**. It does **not** deploy
to any hospital, perform clinical validation, add product features, expand AI, or
make clinical claims. Consistent with the directive's constraint, **no hardware
purchase is recommended** — the framework and evaluation criteria are defined so
a future selection can be justified by evidence and gated by qualification.

## Hardware requirements

`BORESCOPE_HARDWARE_REQUIREMENTS.md` defines MUST/SHOULD/MAY requirements across
optics (resolution, FOV, DoF, focus, illumination, white balance, color),
mechanics (probe diameter/length/articulation/durability), data (lossless
export, machine-readable metadata with **no PHI**, SDK/open export path,
storage, connectivity), power, and lifecycle (support, parts, warranty), plus
explicit **disqualifying conditions**.

## Laboratory design

`PILOT_ZERO_LAB_DESIGN.md` defines 11 functional zones (Intake → Identification
→ Registration → Cleaning Verification → Image Acquisition → Calibration →
Annotation → Review → Secure Storage → Evidence Archiving → Backup), the
evidence flow with a fail-closed quarantine path, roles with separation of
duties, and per-station workstation footprint. Supporting specs:
`IMAGE_ACQUISITION_WORKSTATION.md`, `CALIBRATION_STANDARD.md`,
`LAB_ENVIRONMENT_STANDARD.md`, `LAB_OPERATING_PROCEDURES.md`.

## Qualification results

`HARDWARE_QUALIFICATION_PROTOCOL.md` defines IQ/OQ/PQ with acceptance tests,
repeatability tests, failure criteria, and retest/re-qualification triggers.
**Execution result to date: NOT YET EXECUTED** — this is expected. No physical
lab or device exists to qualify at the documentation stage; the protocol is the
instrument by which a future loaner/unit will be qualified. No PASS is claimed.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Selecting hardware before criteria are applied | Non-repeatable or unusable images | Purchase gated behind scorecard + IQ/OQ/PQ (enforced by this framework) |
| Calibration tolerances unset until a device exists | Ambiguous acceptance | Tolerance table is filled/approved in OQ against the selected device |
| Provenance gaps in captured evidence | Images unusable for datasets | Fail-closed: no identity/calibration/hash → no promotion |
| PHI accidentally entering images/metadata | Governance breach | Instrument-only lab; explicit no-PHI guardrail in every spec |
| Scope creep into clinical/AI work | Violates directive & frozen architecture | Explicit non-goals restated in each document |
| Backup/DR unproven | Evidence loss | Restore test + DR drill are readiness gates (PQ-4, checklist §E) |

## Assumptions

* Pilot Zero images instruments on a **bench**; no patient contact, no
  sterilization requirement (a cleaning procedure suffices).
* A dedicated, access-controlled physical space with conditioned power and an
  isolatable network is available.
* Trained personnel can fill the intake / acquisition / review / lab-lead roles
  with separation of duties.

## Dependencies

* **Physical:** lab space, borescope (loaner for qualification), workstation,
  UPS, isolated network, calibration references, barcode scanner, storage +
  backup media.
* **Program:** Directive 001 (Charter) complete; Directive 002 (Security &
  Engineering Gate) governs the software that will later ingest/govern the
  images.
* **Personnel:** trained operators and a Lab Lead for sign-off.

## Acceptance criteria (for this directive)

All nine required deliverables exist, are internally consistent, vendor-neutral,
and contain no clinical/regulatory/compliance claims; the qualification
framework and selection criteria are complete enough that a future purchase and
lab stand-up can be justified and gated by them.

## Exit criteria (to begin actual image acquisition — future work)

1. A device selected via a completed `BORESCOPE_SELECTION_SCORECARD.md`.
2. `HARDWARE_QUALIFICATION_PROTOCOL.md` executed with **all** IQ/OQ/PQ PASS.
3. `LAB_READINESS_CHECKLIST.md` complete and **signed** (READY).
4. Backup restore + DR drill passed; personnel trained.

## Remaining work (out of scope for this documentation directive)

* Stand up the physical lab; acquire a loaner/unit; execute IQ/OQ/PQ and fill
  the calibration tolerance table.
* Complete scorecards for ≥ 2 candidate devices.
* Train personnel; run the end-to-end evidence and restore/DR drills.
* Sign the readiness checklist.

## Directive completion status

**LPZ-DIR-004 documentation & framework: COMPLETE.**
**Physical laboratory qualification & readiness: NOT STARTED (by design — gated
by this framework and future procurement).**

The directive's mandated deliverables are produced; the lab itself is **not yet
built or qualified**, and this report does not claim otherwise. No hardware
purchase is recommended at this stage.
