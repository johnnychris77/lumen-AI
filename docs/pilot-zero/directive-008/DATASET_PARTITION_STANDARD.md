# LPZ-DIR-008 — Train / Validation / Test Partition Standard

**Purpose:** define partition rules so future candidate-model datasets are
**leakage-free, representative, and reproducible**. This directive does not train
models; it governs how partitions are constructed and validated.

## Requirements

### No data leakage
Train, validation, and test partitions are **disjoint**. No image, and no
information derived from an image, appears in more than one partition. Near-
duplicates (same capture, minor variants) must fall in the **same** partition.

### No duplicate instrument instances across train and test
Partitioning is grouped by **instrument identity / Digital Twin**: all images of a
given physical instrument (same `digital_twin_id` / instrument instance) go to a
**single** partition. A model must never be tested on an instrument it saw in
training. This is the primary leakage guard for reusable instruments.

### Maintain representative distributions
Partitions preserve, as far as feasible, the distribution of key strata: class
(finding) balance, instrument family, manufacturer, and image-quality bands. Where
exact stratification conflicts with the instrument-grouping rule, **instrument
grouping wins** (no leakage), and the resulting distribution skew is documented.

### Document partition rationale
Every dataset version records: the partition method, the grouping key (instrument/
twin), the target ratios (e.g., train/val/test), the strata balanced, and any
documented skew or exclusions.

### Support reproducibility
The partition is deterministic given its inputs and seed. Re-running the
partitioning on the same frozen dataset version yields the same assignment.

### Record random seed where applicable
When randomization is used (e.g., shuffling groups before assignment), the
**seed** is recorded in the dataset manifest so the split is exactly reproducible.

## Partition procedure (governed)

1. **Group by instrument/twin.** Collect all eligible members per instrument
   identity.
2. **Stratify groups**, not images, across partitions to preserve distributions.
3. **Assign whole groups** to train/validation/test at the target ratios.
4. **Verify disjointness** — assert no instrument appears in two partitions and no
   image is shared.
5. **Record** method, seed, ratios, resulting distributions, and any skew.
6. **Freeze** the assignment into the dataset version (`split_assignment`).

## Validation checks (expected outcomes)

* **Leakage check:** intersection of instrument identities across partitions is
  empty → PASS; any overlap → FAIL (blocks approval).
* **Duplicate check:** duplicate images (by `image_sha256`) do not span partitions.
* **Distribution check:** per-stratum proportions reported per partition; large
  unexplained skew is flagged for review.
* **Reproducibility check:** re-running with the recorded seed reproduces the
  identical assignment.

## Governance note (existing system)

`dataset_split` already implements **leakage prevention + stratification**, and
`DatasetRegistryEntry.split_assignment` stores each member's partition;
`dataset_integrity` provides an integrity gate. Governance additions recorded for
a future authorized change: enforce instrument/`digital_twin_id` grouping as the
partition key, persist the partition **seed** and rationale in the manifest, and
add an explicit cross-partition instrument-overlap assertion to the approval gate.
No code is changed under this directive.
