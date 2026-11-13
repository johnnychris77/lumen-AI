# Stage 5D — Leakage-Safe Independent Evaluation Protocol

Status: **protocol + working evaluation code; no real-data evaluation executed.**
The code that enforces this protocol already exists and is tested:
`research/lens_vision/anomaly_experiment.py` (+ `calibration.py`). This document is
the predefined plan that must be frozen **before** the sealed test cohort is opened.

## 1. Predefine before opening the sealed test set

Fixed and recorded before any held-out label is seen:

- **Intended-use conditions & endpoints** — modality (external vs borescope),
  instrument families, anatomy zones, lighting; the anomaly-detection endpoint and
  (where supported) localization endpoint.
- **Error definitions per abnormality** — what counts as a true/false positive and,
  critically, a **false negative** for each class (corrosion, pitting, blood-like,
  bone/tissue-like), plus the **abstention** rule (when the model declines).
- **Cohort sizes** approved by a **statistical reviewer** and a **clinical
  reviewer** before unblinding.

## 2. Four disjoint sets

`fit` → `calibration` → `validation` → **sealed `test`**. Thresholds are frozen on
the dedicated **calibration** set (normal images, at the `1 − target_fpr` quantile)
**before** the held-out evaluation. The sealed test set is opened once.

## 3. Grouping to prevent leakage (enforced in code)

Images are grouped by **physical instrument, specimen, session, study/lab batch, and
exact duplicate (SHA-256)**. The experiment enforces:

- **fit ∩ calibration = ∅** by fine-grained physical identity (specimen / session /
  instrument / inspection / exact image) — a grouped split so one specimen never
  straddles fit and calibration (**calibration-leakage fix**, Stage 5D);
- **(fit ∪ calibration) ∩ test = ∅** by *any* identity token, **including
  laboratory batch**, so a batch effect cannot leak labels into the held-out set.

Lab/facility identity must not act as a shortcut label: cohorts are constructed so
facility/lab is not predictive of the outcome (e.g. each class spans facilities).

## 4. Calibration without test outcomes

Thresholds are fit only on calibration **normals**; test-set outcomes are never used
to choose a threshold. Severity is **never** inferred from anomaly scores.

## 5. Metrics (computed only where scientifically supported)

Per modality (external-camera and borescope **separately**), where sample sizes
permit:

- image-level **AUROC** (+ bootstrap CI), average precision;
- **sensitivity, specificity, false-negative rate, precision** at the frozen
  threshold (+ **Wilson** confidence intervals);
- localization **Dice / IoU** where validated reference masks exist;
- **calibration** quality, **abstention** rate, and **uncertainty** intervals.

Report by instrument family, imaging modality, lighting, anatomy zone, and defect
type **only when data are adequate** for that stratum. **No fabricated denominators,
measurements, or accuracy claims** — a stratum with too few samples is reported as
"insufficient n", not estimated.

## 6. What the current code already does (tested on synthetic fixtures)

`run_anomaly_experiment` performs: research-provenance gate → verified-normal-only
fit → grouped fit/calibration split → **three-way leakage check** → frozen-threshold
calibration → held-out evaluation with AUROC+CI, AP, sensitivity/specificity/FNR at
the frozen threshold (+Wilson CIs), Dice/IoU, per-subgroup AUROC, abstention, and
latency. On synthetic fixtures this is a **technical test only** and is flagged
`synthetic_technical_test`; it is never reported as clinical accuracy.

## 7. Baseline-independent evaluation (see `baseline_independence.py`)

Two arms are compared: **image-only** anomaly localization, and **image + compatible
approved manufacturer baseline**. The baseline may enrich the evidence but must not
overwrite an observed anomaly or authorize release (`assert_baseline_not_authoritative`).

## 8. Outstanding (BLOCKED until provided)

1. The governed instrument/borescope cohorts (`DATASET_ACQUISITION_SPEC.md`).
2. Reviewed ground truth + lab evidence (`GROUND_TRUTH_PROTOCOL.md`).
3. Statistical + clinical reviewer sign-off on endpoints and cohort sizes.
4. Approved, rights-cleared, SHA-256-recorded backbone for the real models.

**No real-data evaluation has been run.** The protocol and its enforcing code are
ready; the executed scientific evaluation is future work.
