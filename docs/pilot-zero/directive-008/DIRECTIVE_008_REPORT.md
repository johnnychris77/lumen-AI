# LPZ-DIR-008 — Directive Report: Dataset Governance & Candidate Model Readiness

## Executive summary

Directive 008 establishes the **governance framework** by which approved Pilot
Zero evidence becomes curated, versioned, reproducible datasets suitable for
**future** candidate computer-vision models. It delivers nine standards (dataset
architecture, classification, creation workflow, versioning, partitioning, quality,
lineage, model-dataset readiness, and this report), each grounded in the dataset
code already present in the repository so the framework is auditable against
reality.

Every dataset governed by this framework is **reproducible, governed, version
controlled, fully traceable, statistically documented, scientifically defensible,
and auditable**, and is **only** constructed from approved evidence (ACTIVE Ground
Truth; approved baselines). This directive is **governance and documentation
only**: no new product functionality, **no model deployment or training**, no
accuracy/clinical-performance claim, and no hospital deployment workflow. No
application code was modified.

## Dataset architecture

`DATASET_ARCHITECTURE.md` defines the dataset as a **manifest over approved
evidence** (reference, don't copy), composing approved images/metadata/annotations/
Ground Truth/baselines/Digital Twins/audit records along the chain Inspection →
Image → Annotation → Ground Truth → Baseline → Digital Twin → Dataset → Candidate
Model (future). Members reference approved evidence by id + `image_sha256`.

## Classification

`DATASET_CLASSIFICATION_STANDARD.md` defines eleven categories (Raw Research,
Quality Approved, Annotation, Ground Truth, Development, Validation, Benchmark,
Training, Test, Retired, Archived) with purpose, permitted uses, approval
authority, lifecycle, and restrictions. Train/validation/test are disjoint and
derived from an approved Ground Truth dataset.

## Workflow

`DATASET_CREATION_WORKFLOW.md`: Approved Images → Metadata Validation → Annotation
Validation → Ground Truth Validation → Baseline Verification → Quality Review →
Dataset Candidate → Engineering Review → Approval → Publication — GT-gated,
fail-closed, with separation of duties, ending in a frozen, checksum-sealed
version.

## Versioning

`DATASET_VERSIONING_STANDARD.md` requires Dataset UUID, version, dates, author,
approver, source references, Ground Truth version, baseline version, Digital Twin
references, checksum, manifest, license, and approval status. **No dataset is
modified after approval**; changes create new versions; manifest + checksums +
pinned GT/baseline versions guarantee reproducibility.

## Quality metrics

`DATASET_QUALITY_STANDARD.md` defines class balance, instrument/manufacturer
diversity, image-quality distribution, annotation agreement, Ground Truth
confidence, Unknown rate, coverage completeness, missing metadata, duplicate
detection, and dataset drift — computed from real records, with "insufficient
data" rather than fabricated figures, and a required per-version quality summary.

## Partition strategy

`DATASET_PARTITION_STANDARD.md` mandates leakage-free, **instrument/Digital-Twin-
grouped** train/validation/test partitions (no instrument instance spans train and
test), representative distributions with documented skew, recorded seed, and
reproducible, deterministic assignment.

## Lineage

`DATASET_LINEAGE_STANDARD.md` guarantees complete, bidirectional lineage Dataset →
Ground Truth → Annotation → Image → Inspection → Instrument → Digital Twin →
Baseline → Evidence Package, with no orphan members, pinned versions, immutable
per-version lineage, and impact analysis.

## Model readiness

`MODEL_DATASET_READINESS_STANDARD.md` defines the ten mandatory, fail-closed
readiness requirements (approval, metadata, no unresolved conflicts, quality
threshold, Ground Truth complete, baseline verified, partition validated, lineage
verified, audit complete, version frozen) and a **readiness certificate** — while
explicitly asserting no model accuracy/clinical claim and authorizing no training.

## Validation procedures (test requirements) & expected outcomes

Documentation-only directive — these are the validation procedures a future
authorized implementation change must satisfy. No tests were added or modified.

| # | Validates | Procedure (future) | Expected outcome |
|---|---|---|---|
| 1 | Dataset creation | Build a dataset including a member without ACTIVE Ground Truth. | Member rejected; approved-evidence-only enforced (fail-closed). |
| 2 | Version creation | Modify an approved dataset. | Rejected; a new version is required (immutability). |
| 3 | Manifest generation | Publish a dataset version. | Manifest enumerates all members + references + partition; reproducible. |
| 4 | Checksum verification | Alter a referenced image after publication. | Checksum mismatch detected against the sealed manifest. |
| 5 | Partition validation | Assign one instrument's images to both train and test. | Leakage check FAILs; blocks approval. |
| 6 | Duplicate detection | Include duplicate images (same `image_sha256`) across partitions. | Duplicates detected; not split across partitions. |
| 7 | Lineage verification | Break a member's GT/image link. | Member flagged ineligible; lineage verification FAILs. |
| 8 | Approval workflow | Approve a dataset as its own author. | Rejected by separation-of-duties; independent approver required. |
| 9 | Dataset immutability | Attempt to add/remove a member from an approved version. | Rejected; approved versions are frozen. |

## Existing-system gap analysis & migration plan

The repository already implements much of this: models `DatasetVersion`,
`DatasetRegistryEntry` (with `image_sha256`, `split_assignment`,
`training_eligibility`, `usage_rights`, `phi_verification`, `lcid`,
`digital_twin_id`, `baseline_id`, `annotation_version`), `ImageQualityAssessment`,
`DoubleBlindReview`; services `dataset_registry`, `dataset_builder`,
`dataset_split` (leakage prevention + stratification), `dataset_integrity`
(reject-gate), `dataset_validation_service`, `dataset_release_service`,
`dataset_export_service`, `dataset_eligibility_service`.

| Gap | Current state | Migration step (future) | Priority |
|---|---|---|---|
| Approved-evidence (GT) precondition | Eligibility referenced, not hard-gated at build | Enforce ACTIVE-GT precondition at member inclusion & approval | High |
| Immutability after approval | Versioning exists | Reject writes to an approved dataset version | High |
| Dataset-level manifest + checksum | Per-image `image_sha256` present | Seal a manifest hash at publication; verify on read | High |
| Instrument-grouped partition key | Leakage-safe split exists | Enforce `digital_twin_id`/instrument grouping + persist seed/rationale | High |
| Pinned GT/baseline versions | ids referenced | Pin GT & baseline **versions** into each member | Medium |
| Category vocabulary | `training_eligibility` flag | Add explicit `dataset_category` | Low |
| Quality summary + drift | Metrics computed piecemeal | Assemble one per-version quality summary + cross-version drift | Medium |
| Readiness certificate | Integrity/eligibility gates exist | Bind all ten readiness checks into one certificate artifact | Medium |

**No migration step is executed under Directive 008.** Each is a candidate for a
future directive that explicitly authorizes code changes. Per the directive's
constraint, **no model training pipeline was implemented** — the existing dataset
machinery is governed, not extended.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Dataset built from unreviewed evidence | Untrustworthy dataset | Approved-evidence-only, GT-gated (planned enforcement) |
| Data leakage across train/test | Inflated future results | Instrument-grouped, leakage-checked partitions |
| Dataset edited after approval | Non-reproducibility | Immutability + new-version rule |
| Silent evidence drift | Dataset no longer matches manifest | Checksums + manifest verification |
| Missing lineage | Not auditable/reproducible | Lineage standard; no orphan members |
| Over-claiming model readiness | False assurance | Readiness = dataset governance only; no model/accuracy claim |
| Scope creep into training/deployment | Violates directive & freeze | Non-goals restated in every doc; candidate model reserved |

## Dependencies

* **Program:** Directives 001, 002, 004, 005, 006, 007 (all complete).
* **System:** the dataset models/services above; LCID identity; annotation/GT and
  baseline governance.
* **Personnel:** dataset authors, engineering reviewers, Dataset Approvers, quality
  auditors, with separation of duties.

## Acceptance criteria

All nine deliverables exist under `docs/pilot-zero/directive-008/`, are internally
consistent and vendor-neutral, make no model accuracy/clinical-performance claim,
enforce approved-evidence-only and dataset immutability, define leakage-free
partitioning and complete lineage, and include validation procedures with expected
outcomes plus an honest gap analysis. **Met.**

## Exit criteria (to operate under this framework — future work)

1. GT-gated dataset creation and separation-of-duties enforced in code.
2. Dataset immutability + sealed manifest/checksum enforced.
3. Instrument-grouped, seed-recorded partitioning enforced.
4. Readiness certificate binding the ten checks produced per dataset version.
5. Validation procedures 1–9 implemented and passing on a clean database.

## Completion status

**LPZ-DIR-008 Dataset Governance & Candidate Model Readiness framework: COMPLETE
(documented).** The framework is defined, grounded in the existing system, and
accompanied by a migration plan and validation procedures. **Code enforcement of
the migration steps is NOT started (by design — deferred to a future authorized
directive).** No machine learning model was implemented, trained, or deployed, and
no accuracy or clinical-performance claim is made.
