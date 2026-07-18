# LPZ-DIR-008 — Dataset Architecture

**Purpose:** define the logical structure of a governed dataset — how approved
Pilot Zero evidence composes into a curated, versioned, reproducible dataset
suitable for **future** candidate computer-vision models. This is a **governance
standard**, not new software; each element is mapped to the dataset code already
present in the repository so the architecture is auditable against reality.

Guardrails: no new product functionality, **no model deployment**, no model
accuracy/clinical-performance claim, no hospital deployment workflow. Datasets are
**only** constructed from approved evidence.

## Sources (governed inputs)

| Source | Meaning | System mapping |
|---|---|---|
| **Approved Images** | Governed captures (Directive 005), integrity-hashed, no PHI | `RetainedImage` / `DatasetRegistryEntry.retained_image_id`, `image_sha256` |
| **Approved Metadata** | Acquisition provenance (Directive 005) | `DatasetRegistryEntry` capture fields |
| **Approved Annotations** | Controlled-taxonomy findings (Directive 006) | `Annotation` / `AnnotationVersion` |
| **Ground Truth** | Human-approved, ACTIVE labels (Directive 006) | `Annotation` GT (ACTIVE) |
| **Baselines** | Approved references (Directive 007) | `BaselineLibraryEntry` / `BaselineImageLink` |
| **Digital Twins** | Instrument identity anchors (Directive 007) | `digital_twin_id` (LCID) |
| **Audit Records** | Attributable lifecycle events | audit trail |

## Relationships

```
Inspection
   ▼
Image           (approved capture, hashed, no PHI)
   ▼
Annotation      (controlled taxonomy, evidence-linked, versioned)
   ▼
Ground Truth    (human-approved, immutable, ACTIVE)
   ▼
Baseline        (approved reference; GT-gated)
   ▼
Digital Twin    (instrument identity anchor)
   ▼
Dataset         (curated, versioned, reproducible composition — this directive)
   ▼
Candidate Model (FUTURE — separate authorized directive; not built here)
```

## Logical dataset structure

A governed dataset is a **manifest over approved evidence**, not a copy of pixels:

* **Dataset identity & version** — `DatasetVersion` (immutable once approved).
* **Members** — `DatasetRegistryEntry` rows, each referencing one approved image
  by id + `image_sha256`, its ACTIVE Ground Truth, baseline, and `digital_twin_id`.
* **Partition** — each member's `split_assignment` (train/validation/test).
* **Provenance** — `lcid`, `usage_rights`, `phi_verification`, `training_eligibility`.
* **Manifest & checksum** — enumerated members + per-image and dataset-level
  checksums for reproducibility (`DATASET_VERSIONING_STANDARD.md`).

## Architectural principles

1. **Reference, don't copy.** The dataset references approved evidence; images
   remain owned by `RetainedImage`. This keeps a single source of truth and makes
   lineage exact.
2. **Approved-evidence-only.** A dataset member must trace to ACTIVE Ground Truth
   and (where used) an approved baseline; unreviewed evidence is ineligible.
3. **Immutable once approved.** A dataset version is frozen at approval; changes
   create a new version (`DATASET_VERSIONING_STANDARD.md`).
4. **Reproducible.** Manifest + checksums + recorded seed reconstruct the exact
   dataset.
5. **Fully traceable.** Every member resolves back through GT → annotation → image
   → inspection → instrument/twin → baseline (`DATASET_LINEAGE_STANDARD.md`).
6. **Tenant-isolated, no PHI.** Enforced across the composition.

## Governance note (existing system)

The repository already implements the spine: `DatasetVersion` +
`DatasetRegistryEntry` (with `image_sha256`, `split_assignment`,
`training_eligibility`, `usage_rights`, `phi_verification`, `lcid`,
`digital_twin_id`, `baseline_id`), and services `dataset_registry`,
`dataset_builder`, `dataset_split` (leakage prevention + stratification),
`dataset_integrity`, `dataset_validation_service`, `dataset_release_service`,
`dataset_export_service`. This architecture **governs** those pieces as one
approved-evidence-only pipeline; it adds no code under this directive. Gaps and a
migration plan are in `DIRECTIVE_008_REPORT.md`.
