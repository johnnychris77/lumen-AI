# LPZ-DIR-010 — Laboratory Readiness Review (LRR)

**Purpose:** verify physical laboratory readiness for governed image acquisition.
Evidence-based; this review distinguishes **framework maturity** from **physical
execution**.

## Review items

| Item | Evidence | Status |
|---|---|---|
| **Qualified hardware** | Directive 004 `BORESCOPE_HARDWARE_REQUIREMENTS.md` + `SELECTION_SCORECARD.md` (framework) | ⚠️ Framework only — no device qualified |
| **Calibration** | `CALIBRATION_STANDARD.md` (tolerances template) | ⚠️ Framework only — not executed against a device |
| **Image acquisition process** | `IMAGE_ACQUISITION_WORKSTATION.md`, SOP-05 | ⚠️ Defined — not operating |
| **Environmental controls** | `LAB_ENVIRONMENT_STANDARD.md` | ⚠️ Defined — lab not stood up |
| **Operator training** | `LAB_OPERATING_PROCEDURES.md` (SOP-01..10) | ⚠️ Curriculum defined — no trained operators recorded |
| **Equipment maintenance** | SOP-09 maintenance | ⚠️ Defined — no equipment in service |
| **Acquisition SOPs** | SOP-01..10 complete | ✅ Complete (documentation) |
| **Image quality validation** | Quality standard + `ImageQualityAssessment` service | ⚠️ Framework/code present — no acquired images |

## Findings

* **LRR-1 (blocking for Alpha execution):** The **physical Pilot Zero laboratory is
  not built**. Directive 004 status is explicit: documentation & framework COMPLETE,
  **physical laboratory qualification & readiness NOT STARTED**. No borescope has
  been selected/qualified, no IQ/OQ/PQ executed, and no governed images acquired.
* **LRR-2 (dependency):** Image quality validation code exists, but with **zero
  acquired Pilot Zero images** there is no operational evidence of end-to-end
  acquisition.
* **LRR-3 (strength):** The complete laboratory framework (requirements, scorecard,
  design, workstation, calibration, environment, SOPs, IQ/OQ/PQ protocol,
  readiness checklist) is documented and ready to execute.

## LRR determination

**NOT READY (framework complete).** The laboratory is fully **specified** but not
**built or qualified**. This is the single largest gap to a real Pilot Alpha that
acquires data. **Condition (mandatory before Alpha execution):** stand up the lab,
select+qualify a borescope via IQ/OQ/PQ, fill the calibration tolerance table,
train operators, and sign the `LAB_READINESS_CHECKLIST.md`. Until then, Pilot Alpha
may proceed only in a **planning / stand-up** posture, not a data-acquiring one.
