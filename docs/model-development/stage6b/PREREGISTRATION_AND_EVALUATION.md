# Stage 6B — Independent Research Evaluation: Pre-Registration & Protocol

Status: **pre-registration template + enforcing code; no real-data evaluation executed.**
The leakage-safe, frozen-threshold evaluation code exists (`anomaly_experiment.py`,
`calibration.py`) and is tested on synthetic fixtures; this document is the plan that
must be **frozen and signed before the sealed-test cohort is opened**.

## 1. Pre-registered elements (fixed before unblinding)

- **Intended use** — anomaly *localization* on reusable surgical instruments, per
  modality (external-camera and borescope evaluated **separately**). Not identity,
  severity, cleanliness, sterility, or patient-safety determination.
- **Research hypotheses** — e.g. "PaDiM/PatchCore detect laboratory-confirmed surface
  anomalies above chance at a pre-set operating point, per modality."
- **Primary endpoints** — image-level detection (per modality); secondary: localization
  where validated masks exist.
- **Error definitions** — per-abnormality true/false positive and, prominently, **false
  negative**; the **abstention** rule.
- **Analysis plan** — frozen thresholds from calibration normals; metrics + CIs; subgroup
  plan; how insufficient-n strata are reported ("insufficient n", never estimated).

## 2. Cohorts & verified group independence

`fit → calibration → validation → sealed_test`, with **verified group independence** via
the Stage 6B comprehensive grouping (instrument / specimen / session / batch / image hash
/ repeat-imaging), across modalities. The sealed-test cohort is opened once.

## 3. Statistical reviewer sign-off (required)

A **statistical reviewer** determines the **minimum cohort size** per modality/split and
the appropriate **confidence-interval** methods **before** data are opened. The readiness
report's `statistical_adequacy` dimension stays *not ready* until this sign-off is
recorded (`statistical_reviewer_signoff`).

## 4. Metrics (computed only where real data support them)

Per modality, where sample sizes permit: image-level **sensitivity, specificity,
false-negative rate, precision, AUROC, average precision**, **abstention**, and
pixel-level **Dice/IoU** where validated masks exist, each with **confidence intervals**.

- **False negatives and difficult visual confounders are reported prominently** (not
  buried in an aggregate), including per-confounder breakdown (reflections, scratches,
  mineral/detergent films, benign discoloration).
- Report by **modality, instrument family**, and other scientifically-supported subgroups.
- **No fabricated denominators, measurements, or accuracy claims.**

## 5. Prohibited claims

An anomaly score **never** establishes material identity, severity, cleanliness,
sterility, or patient safety. Those come only from laboratory confirmation
(`GROUND_TRUTH_VALIDATION.md`) and are never inferred from a score or appearance.

## 6. Outstanding (BLOCKED)

1. Authorized, reviewed real cohorts (external + borescope) meeting the pre-registered
   minimum sizes.
2. Statistical + clinical reviewer sign-off on endpoints and cohort sizes.
3. A license-and-source-verified scientific checkpoint (Stage 6B checkpoint governance).

No real-data evaluation has been run; the protocol and its enforcing code are ready.
