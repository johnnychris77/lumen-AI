# LPZ-DIR-009 — Experiment Governance Standard

**Purpose:** define what every model-development **experiment** must record so it
is reproducible, traceable, and auditable. An experiment that cannot be reproduced
is not trustworthy and cannot advance a model.

## Required experiment fields

| Field | Meaning | System mapping |
|---|---|---|
| **Experiment UUID** | Permanent, immutable identifier | training run id (governance overlay) |
| **Research Objective** | The question the experiment answers | experiment record |
| **Dataset Version** | The frozen, readiness-certified dataset used | `dataset_version` / `dataset_version_id` (Directive 008) |
| **Ground Truth Version** | GT version underlying the dataset | dataset lineage (Directive 006/008) |
| **Baseline Version** | Baseline version(s) referenced | baseline lineage (Directive 007) |
| **Digital Twin Version** | Twin references represented | dataset lineage (Directive 007) |
| **Model Architecture** | Architecture used | `ModelRegistryEntry.architecture` |
| **Hyperparameters** | All tuning parameters | `hyperparameters` |
| **Training Environment** | OS/container/runtime | `training_config` |
| **Random Seed** | Seed(s) for determinism | `training_config` |
| **Software Versions** | Framework + library versions | `framework`, `training_config` |
| **Hardware** | Compute used | experiment record |
| **Author** | Who ran it | experiment author |
| **Reviewer** | Who reviewed it (independent) | `reviewer` |
| **Results** | Metrics + artifacts produced | `training_metrics`, `evaluation_metrics` |
| **Approval Status** | Draft / reviewed / approved | `approval_status` |

## Rules

1. **Frozen-dataset input.** An experiment must reference a **readiness-certified,
   frozen** dataset version (Directive 008) — never a mutable or uncertified set.
2. **Reproducibility complete.** Seed, software/hardware, environment, and git
   commit must be recorded such that the run can be re-executed and verified.
3. **Fully specified.** All hyperparameters and architecture details are recorded;
   nothing material is left implicit.
4. **Lineage pinned.** Dataset, Ground Truth, baseline, and Digital Twin
   **versions** are pinned so results are interpretable against exact evidence.
5. **Independent review.** The reviewer is not the author.
6. **Immutable record.** An experiment record is append-only; corrections create a
   new experiment or a linked amendment, never an overwrite.
7. **Attributable.** Author, reviewer, timestamps, and approval are recorded.

## Reproducibility check (expected outcome)

Given an experiment's recorded config, seed, software/hardware, and dataset
version, re-running the pipeline reproduces the same model artifact (or a
documented, bounded difference). A run that cannot be reproduced is flagged and
cannot support promotion (`reproducible_training_confirmed` gate).

## Governance note (existing system)

`training_config` provides reproducible configuration (seed, environment,
software), `candidate_training` orchestrates runs, and `ModelRegistryEntry`
records architecture, hyperparameters, framework, git_commit, preprocessing
version, and training/evaluation metrics with a `reproducible_training_confirmed`
flag. Governance additions recorded for a future authorized change: a first-class
**Experiment** record with its own UUID binding all fields above (including pinned
GT/baseline/twin versions and hardware) and an append-only amendment model. No
code is changed under this directive.
