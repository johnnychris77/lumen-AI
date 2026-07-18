# LPZ-DIR-008 — Dataset Quality Standard

**Purpose:** define the metrics that describe a dataset's quality and
composition, so datasets are **statistically documented and scientifically
defensible**. Metrics describe the **data**, not any model. This directive
computes no model performance and makes no accuracy claim.

Guardrail: every metric is computed from real dataset records; where data is
insufficient, the metric reports "insufficient data", never a fabricated figure.

## Metric definitions

| Metric | Definition | Purpose |
|---|---|---|
| **Class balance** | Distribution of finding/label classes | Detect over/under-representation |
| **Instrument diversity** | Distinct instruments / families represented | Generalization coverage |
| **Manufacturer diversity** | Distinct manufacturers represented | Avoid single-vendor bias |
| **Image quality distribution** | Members by quality band (Excellent…Reject) | Ensure adequate quality mix |
| **Annotation agreement** | Inter-reviewer agreement of member annotations | Label reliability (Directive 006) |
| **Ground Truth confidence** | Distribution of reviewer-confidence bands | Trust level of labels |
| **Unknown rate** | Share of members labeled Unknown/Unable to Determine | Honest uncertainty; taxonomy coverage |
| **Coverage completeness** | Share of members with required regions imaged | Comparison validity |
| **Missing metadata** | Share of members missing required metadata | Data completeness gate |
| **Duplicate detection** | Duplicate/near-duplicate members (by `image_sha256`) | Leakage & inflation guard |
| **Dataset drift** | Distribution shift vs. a prior version/benchmark | Composition stability over versions |

## Interpretation rules

* **Unknown rate is not a failure metric.** A dataset that honestly records
  uncertainty is more defensible than one that forces labels; a rising trend may
  signal a taxonomy gap.
* **Diversity vs. balance trade-offs** are documented, not silently optimized;
  instrument-grouping for leakage-safety (`DATASET_PARTITION_STANDARD.md`) takes
  precedence over perfect class balance.
* **Duplicates** must be resolved before approval — near-duplicates are kept in a
  single partition or removed, never split across train/test.
* **Missing metadata / coverage gaps** reduce eligibility; members below the bar
  are excluded, with the exclusion documented.

## Documentation requirement

Every published dataset version ships a **quality summary** recording each metric
(or "insufficient data"), the strata reported, exclusions, and any documented
skew. This summary is part of the dataset's statistical documentation and is
required for model-dataset readiness (`MODEL_DATASET_READINESS_STANDARD.md`).

## Thresholds

This directive does **not** set numeric pass/fail thresholds beyond structural
gates (no unresolved duplicates across partitions; required metadata present for
eligible members; audit completeness). Credible thresholds require baseline data
from the operating program and are set later under a separate authorized
directive.

## Governance note (existing system)

`ImageQualityAssessment`, `dataset_validation_service`, `dataset_integrity`, and
the annotation analytics service already compute quality, integrity, agreement,
and Unknown-rate signals from real records; `image_sha256` supports duplicate
detection. Governance additions recorded for a future authorized change: assemble
a single dataset-version **quality summary** artifact covering all metrics above,
and add cross-version drift reporting. No code is changed under this directive.
