# LPZ-DIR-004 — Laboratory Environment Standard

**Purpose:** define the environmental, power, network, physical-security, and
recovery requirements for the Pilot Zero Laboratory so image acquisition is
stable, secure, and traceable. Engineering laboratory only — no clinical or
sterile-processing claim.

## 1. Temperature

* Maintain a stable ambient temperature within a documented comfort/equipment
  band (e.g., a set point with a modest tolerance) to keep the imaging chain and
  computers within spec.
* Record temperature at session start; log excursions.

## 2. Humidity

* Maintain relative humidity within a documented band to avoid condensation and
  static.
* Record at session start; log excursions.

## 3. Dust / particulate control

* Keep the acquisition area clean and low-dust; wipe surfaces and the probe per
  the cleaning procedure below.
* No food/drink at acquisition or review stations.

## 4. Lighting

* Controlled, consistent ambient lighting at acquisition and review; no direct
  glare on the probe field or the review display.
* Ambient light must not contaminate captures (calibration verifies this).

## 5. Power

* Conditioned power; workstation + illumination + capture appliance on **UPS**
  (see `IMAGE_ACQUISITION_WORKSTATION.md`).
* Surge protection; documented circuits.

## 6. Network

* **Isolated/segmented lab network**; only capture, storage, and backup hosts
  attached. Default is no general internet exposure.
* NTP time sync for trustworthy timestamps.
* Any external sync is an explicit, reviewed exception.

## 7. Physical security

* The lab is a controlled-access space. Instruments, workstations, storage, and
  archive media are physically secured when unattended.
* Removable media is controlled; nothing leaves the lab uncontrolled.

## 8. Access control

* Named individuals only; access tied to role (intake / acquisition / review /
  lab lead).
* Workstation accounts are individual (no shared logins); least privilege.
* Access list reviewed periodically; departures revoke access promptly.
* **Separation of duties:** the reviewer for an image set differs from its
  acquirer.

## 9. Probe / equipment cleaning (engineering, non-clinical)

* Wipe-down procedure for the probe and staging jig between instruments to keep
  optics clean and avoid cross-contamination of the **image** (not a
  sterilization claim; no patient contact occurs).
* Cleaning materials and cadence documented; damaged probes quarantined.

## 10. Backup

* 3-2-1 backups of evidence + provenance (see
  `IMAGE_ACQUISITION_WORKSTATION.md` §3). Scheduled, logged, restore-tested.

## 11. Disaster recovery

* Documented recovery procedure: how to restore secure storage and archive from
  backup, with a target recovery objective recorded during qualification.
* Recovery drill performed and recorded before readiness sign-off, and
  periodically thereafter.
* Archive is write-once/append-only so accepted evidence survives a working-copy
  loss.

## 12. Data governance guardrails (non-negotiable)

* **No PHI** enters the lab, the images, or the metadata — instruments only.
* No image is promoted into a dataset without complete provenance and a valid
  integrity hash.
* No clinical, diagnostic, or regulatory claim is made by operating this lab; no
  claim of HIPAA, SOC 2, ISO 13485, IEC 62304, ISO 14971, or 21 CFR Part 11
  compliance is made.

## Records

Environmental readings, access reviews, cleaning logs, backup/restore tests, and
DR drills are logged and archived as evidence supporting the
`LAB_READINESS_CHECKLIST.md`.
