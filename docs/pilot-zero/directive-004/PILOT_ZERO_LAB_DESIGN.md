# LPZ-DIR-004 — Pilot Zero Laboratory Design

**Purpose:** define the physical and workflow design of the Pilot Zero
Laboratory — the controlled engineering environment used to produce **governed
image evidence** of surgical instruments for **future** computer-vision dataset
development. This is not a hospital, not a clinical site, and not a sterile
processing department; it is an engineering lab. No clinical activity occurs
here.

## Design principles

1. **Chain of custody / traceability** — every image is traceable to an
   instrument identity, a capture station, a device, an operator, and a
   timestamp.
2. **Repeatability** — fixed geometry, fixed lighting, calibrated capture, so
   images are comparable across sessions.
3. **Separation of duties** — acquisition, review, and archiving are distinct
   steps with distinct sign-offs.
4. **Fail-closed evidence handling** — an image without complete provenance is
   quarantined, never promoted into a dataset.
5. **No PHI** — instruments only; no patient data enters the lab or the image
   metadata.

## Zone layout (functional zones — may be co-located in a single room with
clear demarcation)

```
 ┌──────────────┐   ┌───────────────┐   ┌──────────────────┐
 │ 1. Intake    │──▶│ 2. Identify   │──▶│ 3. Registration  │
 │ (receiving)  │   │ (barcode/UDI) │   │ (system record)  │
 └──────────────┘   └───────────────┘   └────────┬─────────┘
                                                  ▼
 ┌──────────────┐   ┌───────────────┐   ┌──────────────────┐
 │ 6. Calibration│◀─│ 5. Image      │◀──│ 4. Cleaning      │
 │ (pre-session)│   │ Acquisition   │   │ Verification*    │
 └──────────────┘   └──────┬────────┘   └──────────────────┘
                           ▼
 ┌──────────────┐   ┌───────────────┐   ┌──────────────────┐
 │ 7. Annotation│──▶│ 8. Review     │──▶│ 9. Secure Storage│
 └──────────────┘   └───────────────┘   └────────┬─────────┘
                                                  ▼
                    ┌───────────────┐   ┌──────────────────┐
                    │ 11. Backup    │◀──│ 10. Evidence     │
                    │               │   │ Archiving        │
                    └───────────────┘   └──────────────────┘
```

\* *Cleaning Verification* here means confirming the instrument's surface
condition/state is recorded before imaging (a bench engineering check), **not**
a clinical reprocessing claim.

## Zone specifications

| Zone | Function | Key requirements | Sign-off |
|---|---|---|---|
| 1. Instrument Intake | Receive & log instruments into the lab | Physical inbound log; damage check; segregation area | Intake operator |
| 2. Identification | Read instrument identity (barcode/QR/UDI or manual) | Barcode scanner; fallback manual entry with dual-check | Intake operator |
| 3. Registration | Create the governed instrument record | Recorded before any capture; unique lab instrument ID | Intake operator |
| 4. Cleaning Verification | Record surface state/condition prior to imaging | Documented condition note; photographs of state if required | Acquisition operator |
| 5. Image Acquisition | Capture calibrated images | Fixed mount/geometry, calibrated lighting, per `IMAGE_ACQUISITION_WORKSTATION.md` | Acquisition operator |
| 6. Calibration | Verify capture chain before/within a session | Per `CALIBRATION_STANDARD.md`; results logged | Acquisition operator |
| 7. Annotation | Attach engineering labels/metadata (non-clinical) | Labels are engineering descriptors only; no diagnosis | Annotator |
| 8. Review | Second-person QC of image + provenance completeness | Reject/quarantine path for incomplete provenance | Reviewer (≠ acquirer) |
| 9. Secure Storage | Store reviewed evidence | Access-controlled; integrity-hashed; per `LAB_ENVIRONMENT_STANDARD.md` | Lab lead |
| 10. Evidence Archiving | Immutable archival of accepted evidence | Write-once/append-only archive; retention policy | Lab lead |
| 11. Backup | Independent backup copy | Off-primary backup; restore-tested | Lab lead |

## Workstation footprint (per acquisition station)

* Bench with a **fixed camera/probe mount** and a defined instrument staging
  jig so geometry is repeatable (standoff distance, angle).
* Controlled, calibrated lighting (see `LAB_ENVIRONMENT_STANDARD.md`).
* Acquisition computer + calibrated display (see
  `IMAGE_ACQUISITION_WORKSTATION.md`).
* Barcode scanner for instrument identification.
* Local capture storage feeding secure storage; no removable media leaves the
  lab uncontrolled.

## Data / evidence flow

```
Instrument ID (Zone 2/3)
   └─▶ Session opened → Calibration verified (Zone 6)
         └─▶ Capture (Zone 5) → image + provenance metadata (no PHI)
               └─▶ Annotation (Zone 7) → Review/QC (Zone 8)
                     └─▶ Accept → Secure Storage (Zone 9)
                           └─▶ Archive (Zone 10) → Backup (Zone 11)
                     └─▶ Reject → Quarantine (re-capture or discard, logged)
```

## Roles (minimum)

* **Intake operator** — receiving, identification, registration.
* **Acquisition operator** — calibration, capture.
* **Reviewer** — independent QC (must differ from the acquisition operator for
  the same image set).
* **Lab lead** — storage/archive/backup governance, readiness sign-off.

## Constraints & disclaimers

* No clinical, diagnostic, or regulatory claim is made by operating this lab.
* No AI/model capability is created by this directive; the lab produces the raw,
  governed evidence that a **future** directive may use for dataset/model work.
* Physical security, access control, and environmental controls are specified
  in `LAB_ENVIRONMENT_STANDARD.md`.
