# LPZ-DIR-008 — Dataset Lineage Standard

**Purpose:** guarantee that every dataset supports **complete, reconstructable
lineage** back to the physical instrument and the approved evidence it was built
from. Lineage is what makes a dataset auditable and scientifically defensible.

## Lineage chain

```
Dataset            (version, manifest, checksum)
   ▼
Ground Truth       (ACTIVE version each member resolves to)
   ▼
Annotation         (version, controlled taxonomy, evidence)
   ▼
Image              (RetainedImage, image_sha256)
   ▼
Inspection         (inspection event)
   ▼
Instrument         (instrument identity / UDI)
   ▼
Digital Twin       (governed identity anchor)
   ▼
Baseline           (approved reference version used)
   ▼
Evidence Package   (assembled, auditable bundle)
```

## Lineage requirements

For **every dataset member**, the following must be recorded and resolvable:

| Link | Recorded reference | System mapping |
|---|---|---|
| Dataset → member | member row | `DatasetRegistryEntry` (in `DatasetVersion`) |
| member → Ground Truth | GT version | `Annotation` GT (ACTIVE) |
| member → Annotation | annotation version | `annotation_version` |
| member → Image | image id + checksum | `retained_image_id`, `image_sha256` |
| member → Inspection | inspection id | `inspection_id` |
| member → Instrument | instrument identity | `instrument_id`, `lcid` |
| member → Digital Twin | twin id | `digital_twin_id` |
| member → Baseline | baseline id/version | `baseline_id` |
| member → Evidence Package | assembled bundle | evidence/audit facility |

## Rules

1. **No orphan members.** A dataset member with a broken link (missing GT, image,
   or identity) is ineligible — fail-closed.
2. **Versions pinned.** Lineage records the exact GT and baseline **versions**, so
   the dataset is reproducible even after those evolve.
3. **Bidirectional traceability.** From a dataset one can reach every source; from
   a piece of evidence one can find every dataset version that uses it (impact
   analysis, e.g., if evidence is retired).
4. **Immutable lineage.** Lineage for an approved dataset version is frozen with
   the version; corrections create a new version.
5. **Auditable end-to-end.** The full chain is reconstructable from stored
   references + audit trail; no link is inferred or fabricated.

## Uses of lineage

* **Audit:** prove a dataset was built only from approved evidence.
* **Reproduction:** rebuild and verify a past dataset version.
* **Impact analysis:** if an image, annotation, GT, or baseline is corrected or
  retired, identify every dataset version affected.
* **Model-readiness:** lineage verification is a required readiness gate
  (`MODEL_DATASET_READINESS_STANDARD.md`).

## Governance note (existing system)

`DatasetRegistryEntry` already carries the linking columns (`retained_image_id`,
`image_sha256`, `inspection_id`, `instrument_id`, `lcid`, `digital_twin_id`,
`baseline_id`, `annotation_version`) and `DatasetVersion` groups members; the LCID
services maintain identity. Governance additions recorded for a future authorized
change: pin GT/baseline **versions** into each member, add a reverse
evidence→datasets index for impact analysis, and produce a per-dataset lineage
report as part of publication. No code is changed under this directive.
