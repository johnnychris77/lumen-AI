# LPZ-DIR-008 — Dataset Creation Workflow

**Purpose:** define the governed path by which approved evidence becomes a
published, reproducible dataset. Datasets are **only** built from approved
Pilot Zero evidence; each gate is fail-closed.

## Workflow

```
Approved Images           (Directive 005 — hashed, no PHI)
      ▼
Metadata Validation       (acquisition provenance complete)
      ▼
Annotation Validation     (Directive 006 — controlled taxonomy, evidence)
      ▼
Ground Truth Validation   (Directive 006 — ACTIVE, human-approved)
      ▼
Baseline Verification     (Directive 007 — approved baseline where used)
      ▼
Quality Review            (image quality + composition adequacy)
      ▼
Dataset Candidate         (manifest assembled; partition proposed)
      ▼
Engineering Review        (partition, leakage, distributions, reproducibility)
      ▼
Approval                  (Dataset Approver; separation of duties)
      ▼
Publication               (version frozen; manifest + checksums sealed)
```

## Stage detail

### 1. Approved Images
Only governed, integrity-hashed, PHI-verified images (Directive 005) are eligible.
*System:* `DatasetRegistryEntry.retained_image_id` + `image_sha256`,
`phi_verification`.

### 2. Metadata Validation
Required acquisition metadata is present and consistent (device, resolution,
lighting, instrument identity). Missing required metadata → excluded.
*System:* `dataset_validation_service`, registry capture fields.

### 3. Annotation Validation
Each candidate member has a valid annotation under the Directive 006 taxonomy with
evidence references. *System:* `Annotation` link, `annotation_version`.

### 4. Ground Truth Validation
Each member must resolve to **ACTIVE** Ground Truth — the "approved evidence only"
rule. Non-GT members are ineligible (fail-closed). *System:* GT status check.

### 5. Baseline Verification
Where the dataset's purpose involves baseline comparison, the referenced baseline
must be an **approved** version (Directive 007). *System:* `baseline_id`,
baseline lifecycle.

### 6. Quality Review
Image quality distribution and composition adequacy are reviewed; poor-quality or
unrepresentative members are handled per `DATASET_QUALITY_STANDARD.md`.

### 7. Dataset Candidate
The manifest (members + references + proposed partition) is assembled. Not yet
usable. *System:* `dataset_builder`, `DatasetVersion` (draft).

### 8. Engineering Review
An Engineering Reviewer verifies the partition (no leakage, no duplicate
instrument instances across train/test), distributions, seed, and reproducibility
(`DATASET_PARTITION_STANDARD.md`). *System:* `dataset_split`, `dataset_integrity`.

### 9. Approval
A **Dataset Approver** (not the dataset's author) approves per governance,
recording approver, timestamp, rationale, source references, GT/baseline versions,
checksum, and manifest. *System:* approval fields on `DatasetVersion`.

### 10. Publication
The dataset version is **frozen**: manifest and checksums are sealed, and the
version becomes citable for future candidate-model readiness. **No modification
after approval** — changes create a new version. *System:* frozen `DatasetVersion`.

## Invariants

* **Approved-evidence-only** and **GT-gated** at member level.
* **Fail-closed:** any missing validation, evidence, or partition check blocks
  progression.
* **Separation of duties:** approver ≠ dataset author/engineering reviewer of the
  same version where feasible.
* **Reproducible:** manifest + checksums + seed recorded before publication.
* **Immutable once approved:** new versions, never edits.

## Governance note (existing system)

`dataset_builder`, `dataset_registry`, `dataset_split`, `dataset_integrity`,
`dataset_validation_service`, and `dataset_release_service` already implement much
of this pipeline (leakage-safe splitting, integrity gate, validation, release
builder). Governance additions recorded for a future authorized change: enforce
the ACTIVE-Ground-Truth precondition and separation-of-duties at the approval
boundary, and seal a manifest + dataset-level checksum at publication. No code is
changed under this directive.
