# LPZ-DIR-008 — Model-Dataset Readiness Standard

**Purpose:** define the **minimum requirements a dataset must meet before it may be
used for future candidate model training**. This is a governance gate on the
*dataset*, not a model. **No model is trained, deployed, or evaluated under this
directive**, and no accuracy or clinical-performance claim is made.

## Readiness requirements (all mandatory)

A dataset version is **model-ready** only when **every** item below is satisfied
and recorded:

| # | Requirement | Evidence |
|---|---|---|
| 1 | **Approval complete** | Dataset version approved by an authorized Dataset Approver (separation of duties). |
| 2 | **Metadata complete** | All eligible members have required acquisition metadata; missing-metadata members excluded. |
| 3 | **No unresolved review conflicts** | No member carries an open annotation disagreement (Directive 006). |
| 4 | **Quality threshold achieved** | Quality summary produced; structural quality gates pass (duplicates resolved, coverage/metadata bars met). |
| 5 | **Ground Truth complete** | Every member resolves to ACTIVE Ground Truth (Directive 006). |
| 6 | **Baseline verified** | Referenced baselines are approved versions (Directive 007). |
| 7 | **Partition validated** | Leakage-free, instrument-grouped train/val/test with recorded seed and rationale (`DATASET_PARTITION_STANDARD.md`). |
| 8 | **Lineage verified** | Complete lineage for every member (`DATASET_LINEAGE_STANDARD.md`). |
| 9 | **Audit complete** | All lifecycle transitions have attributable audit events (audit completeness = 100%). |
| 10 | **Dataset version frozen** | Manifest + checksums sealed; version immutable (`DATASET_VERSIONING_STANDARD.md`). |

## Readiness rule

**Fail-closed:** if any requirement is unmet, the dataset is **not** model-ready.
There is no partial-ready state — readiness is all-or-nothing and attributable.
A readiness determination records who certified it, when, against which dataset
version, and the evidence for each of the ten items.

## What readiness does NOT assert

* It does **not** claim any model will be accurate or clinically valid.
* It does **not** authorize training, deployment, or evaluation — those require a
  separate, explicitly-authorized directive.
* It certifies only that the **dataset** is governed, reproducible, traceable,
  documented, and frozen — a precondition for *future* candidate work.

## Readiness certificate (artifact)

On passing, a **readiness certificate** is recorded: dataset UUID + version,
certifier, timestamp, the ten items with evidence references, the quality summary,
the partition report, and the lineage report. The certificate is the auditable
statement that the dataset may proceed to future candidate model development.

## Governance note (existing system)

`DatasetRegistryEntry.training_eligibility`, `dataset_integrity` (reject-gate),
`dataset_validation_service`, and the eligibility/release services already gate
training-eligibility and integrity today. Governance additions recorded for a
future authorized change: assemble a single **readiness certificate** binding all
ten checks to a frozen dataset version, and require it before any candidate
training directive may consume the dataset. No code is changed under this
directive.
