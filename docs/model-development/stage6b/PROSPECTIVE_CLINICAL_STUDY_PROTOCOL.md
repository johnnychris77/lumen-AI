# Stage 6B — Prospective Clinical-Study Protocol & Readiness Determination

## Determination

**`NOT_READY_FOR_PROSPECTIVE_CLINICAL_VALIDATION`**

A prospective, observational, non-interventional evaluation may be prepared only after
real-image scientific benchmark evidence exists and has been independently reviewed.
That evidence does not yet exist (see `STAGE_6B_REPORT.md`), so no prospective clinical
study may begin. This document is the **protocol template** to be completed once the
prerequisites are met; it authorizes nothing by itself.

## Non-negotiable constraints

- The study is **observational and non-interventional**: a research model **must not
  influence instrument release or technician disposition**, enter the Lumen Decision
  Engine, clinical serving, or manufacturer intelligence. Clinical decisions remain with
  the responsible clinical staff and the existing validated workflow.
- Separate **institutional / ethics (IRB)** approval and the existing governance gates
  are required before any prospective activity.

## Protocol template (to complete when prerequisites are met)

1. **Intended use & claim** — the exact, narrow intended use being evaluated; explicitly
   not identity/severity/cleanliness/sterility/patient-safety.
2. **Institutional / ethics determination** — IRB/ethics decision, data-use agreements,
   privacy determination; authorization for any facility/clinical-adjacent data.
3. **Study population & setting** — instrument families, facilities, inclusion/exclusion.
4. **Image-acquisition workflow** — external-camera and borescope capture procedure,
   device/lighting standardization, quality control, PHI handling.
5. **Blinded reference standard** — the independent ground truth (laboratory/expert
   review) against which model outputs are compared, with blinding procedure.
6. **Sample-size justification** — statistician-approved powering for the prospective
   endpoints and confidence intervals.
7. **Safety-monitoring process** — missed-finding / out-of-scope monitoring, periodic
   review, adverse-signal handling (reusing the existing shadow-validation safety
   monitor concepts).
8. **Stopping rules** — predefined criteria to pause/stop (safety, futility, data quality).
9. **Responsibility for clinical decisions** — explicit statement that clinical staff and
   the validated workflow retain decision authority; the model is non-actionable.
10. **Analysis & reporting plan** — prospective endpoints, subgroup plan, handling of
    abstention and confounders, pre-registration.

## Prerequisites before this protocol may be activated (all currently missing)

1. A completed, independently-reviewed **real-image research benchmark** (external +
   borescope) with reported metrics + CIs — i.e. `BLOCKED_REAL_IMAGE_BENCHMARK` cleared.
2. **Statistical + clinical** reviewer approval of those results and the intended use.
3. **Institutional / ethics** approval for a prospective, observational study.
4. A **license-and-source-verified** scientific checkpoint and governed, authorized data.

Until all four exist, the determination remains
**`NOT_READY_FOR_PROSPECTIVE_CLINICAL_VALIDATION`**.
