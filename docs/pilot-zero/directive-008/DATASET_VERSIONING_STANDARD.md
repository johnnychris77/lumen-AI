# LPZ-DIR-008 — Dataset Versioning Standard

**Purpose:** define how datasets are versioned. Core rule: **no dataset is
modified after approval — new versions are created**, and every version is
reproducible from its manifest and checksums.

## Required dataset fields

| Field | Meaning | System mapping |
|---|---|---|
| **Dataset UUID** | Permanent, immutable identity | `DatasetVersion` id |
| **Version** | Monotonic version | `DatasetVersion` version / label |
| **Creation Date** | When created | `created_at` |
| **Author** | Who assembled it | author field |
| **Approver** | Who approved it (attributable) | approver field |
| **Source References** | Member evidence (images, annotations) | `DatasetRegistryEntry` rows (id + `image_sha256`) |
| **Ground Truth Version** | GT version each member resolves to | `Annotation` GT version |
| **Baseline Version** | Baseline version(s) used | `baseline_id` + baseline version |
| **Digital Twin References** | Instrument twins represented | `digital_twin_id` set |
| **Checksum** | Per-image + dataset-level integrity | `image_sha256` + dataset manifest hash |
| **Manifest** | Enumerated members + partition | manifest artifact |
| **License** | Usage rights | `usage_rights` |
| **Approval Status** | Draft / Approved / Published / Superseded / Retired | `DatasetVersion` status |

## Versioning rules

1. **Immutable after approval.** Once approved/published, a dataset version is
   frozen. No member is added, removed, or relabeled in place.
2. **New version for any change.** Adding data, fixing a label, or re-partitioning
   creates a **new** dataset version with its own UUID/version, manifest, and
   checksums; the prior version is retained and marked Superseded.
3. **Manifest is authoritative.** The manifest enumerates every member (image id +
   `image_sha256`), its GT/baseline/twin references, and its partition — enough to
   reconstruct the dataset exactly.
4. **Checksums verify integrity.** Each member carries `image_sha256`; the dataset
   carries a manifest-level checksum. Verification detects any drift between the
   recorded manifest and the referenced evidence.
5. **Reason required.** Every new version records why it was created.
6. **Retrievable history.** Superseded versions remain retrievable for audit and
   to reproduce past work.
7. **Frozen references.** A dataset version pins the exact **GT version** and
   **baseline version** of each member, so it is reproducible even after GT or
   baselines evolve.

## Lineage example

```
DATASET 2026-000007
  v1  approved 2026-04-01  approver=A  manifest#… checksum#…  reason="initial GT dataset"
  v2  approved 2026-05-15  approver=B  manifest#… checksum#…  reason="added 40 GT members; re-split"  supersedes v1
       (v1 retained, marked Superseded — never edited)
```

## Reproducibility guarantee

Given a dataset version's manifest, checksums, and recorded partition seed, the
exact dataset (members + partition) can be reconstructed and verified. A mismatch
between manifest and referenced evidence is a governance failure surfaced by
checksum verification, not silently ignored.

## Governance note (existing system)

`DatasetVersion` versions datasets today, `DatasetRegistryEntry.image_sha256`
provides per-image checksums, `dataset_integrity` gates integrity, and
`dataset_release_service` builds releases. Governance additions recorded for a
future authorized change: seal a dataset-level manifest hash at approval, pin GT
and baseline **versions** into each member record, and make "no modification after
approval" an enforced invariant (writes to an approved version rejected). No code
is changed under this directive.
