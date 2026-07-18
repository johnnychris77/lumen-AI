# LPZ-DIR-008 — Dataset Classification Standard

**Purpose:** define dataset categories so every dataset has a declared purpose,
permitted uses, approval authority, lifecycle, and restrictions. Categories
describe **trust level and intended use**, not model performance.

Guardrail: no category implies model accuracy or clinical performance; the
"training/validation/test" categories describe **data role**, not any trained
model's quality.

## Categories

### Raw Research Dataset
* **Purpose:** exploratory collection of evidence for internal study.
* **Permitted uses:** research/exploration only.
* **Approval authority:** AI Researcher (research-only flag).
* **Lifecycle:** Draft → Retired/Archived.
* **Restrictions:** never used for candidate model training; may contain
  not-yet-approved evidence and must be labeled research-only.

### Quality Approved Dataset
* **Purpose:** evidence that has passed image-quality review.
* **Permitted uses:** input to annotation/Ground Truth datasets.
* **Approval authority:** Quality Reviewer.
* **Lifecycle:** Draft → Approved → Superseded.
* **Restrictions:** quality-approved ≠ training-ready; GT still required.

### Annotation Dataset
* **Purpose:** images with completed annotations (pre-Ground-Truth).
* **Permitted uses:** review, adjudication, GT assembly.
* **Approval authority:** Annotation/Review governance (Directive 006).
* **Lifecycle:** Draft → Approved → Superseded.
* **Restrictions:** not training-ready until GT is ACTIVE.

### Ground Truth Dataset
* **Purpose:** images with **ACTIVE** human-approved Ground Truth.
* **Permitted uses:** basis for development/training/validation/test datasets.
* **Approval authority:** Ground Truth Approver (Directive 006).
* **Lifecycle:** Approved → Superseded (new GT version).
* **Restrictions:** the foundational trusted layer; never bypassed.

### Development Dataset
* **Purpose:** curated dataset for model development iteration.
* **Permitted uses:** future development/experimentation.
* **Approval authority:** Dataset Approver + Engineering Reviewer.
* **Lifecycle:** Candidate → Approved → Published → Superseded/Retired.
* **Restrictions:** development context; not a benchmark of record.

### Validation Dataset
* **Purpose:** partition used to tune/select during future development.
* **Permitted uses:** model selection (future work).
* **Approval authority:** Dataset Approver.
* **Lifecycle:** frozen with its parent dataset version.
* **Restrictions:** disjoint from train and test (`DATASET_PARTITION_STANDARD.md`).

### Benchmark Dataset
* **Purpose:** a governed, stable dataset for comparison over time.
* **Permitted uses:** future benchmarking; held stable.
* **Approval authority:** Dataset Approver + Program Administrator.
* **Lifecycle:** Approved → Published (long-lived) → Superseded.
* **Restrictions:** changes require a new version; never silently edited.

### Training Dataset
* **Purpose:** partition designated for future candidate model training.
* **Permitted uses:** future training (no training under this directive).
* **Approval authority:** Dataset Approver.
* **Lifecycle:** frozen with its parent dataset version.
* **Restrictions:** disjoint from validation and test; no instrument-instance
  leakage.

### Test Dataset
* **Purpose:** held-out partition for future unbiased evaluation.
* **Permitted uses:** future evaluation only.
* **Approval authority:** Dataset Approver; access-restricted.
* **Lifecycle:** frozen; ideally sealed until evaluation.
* **Restrictions:** never seen in train/validation; strict no-leakage.

### Retired Dataset
* **Purpose:** a dataset withdrawn from use.
* **Permitted uses:** none for new work; retained for audit.
* **Approval authority:** Dataset Approver records retirement + reason.
* **Lifecycle:** Retired → Archived.
* **Restrictions:** not selectable for new development.

### Archived Dataset
* **Purpose:** immutable historical retention.
* **Permitted uses:** audit, lineage, reproduction of past work.
* **Approval authority:** system-preserved.
* **Lifecycle:** terminal; nothing leaves Archived.
* **Restrictions:** read-only.

## Cross-category rules

* **Training/validation/test are disjoint** and derived from an approved Ground
  Truth Dataset (`DATASET_PARTITION_STANDARD.md`).
* **Only approved, frozen dataset versions** feed candidate-model readiness
  (`MODEL_DATASET_READINESS_STANDARD.md`).
* **Tenant isolation & no PHI** apply to every category.
* **No overwrite:** category/version changes create new versions.

## Governance note (existing system)

Today `DatasetRegistryEntry` carries `training_eligibility` and `split_assignment`,
and `DatasetVersion` versions the dataset; the builder/eligibility/release services
distinguish research vs. training-eligible data. This standard formalizes the
category vocabulary as a governance overlay; a future authorized change may add an
explicit `dataset_category` field. No code is changed under this directive.
