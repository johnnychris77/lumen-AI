# LumenAI Clinical Image Dataset (LCID) — Dataset Specification

**Status:** This sprint does not train an AI model. It formalizes the
governed dataset infrastructure every future computer-vision model must be
built on, additively extending the Dataset Registry & AI Model Development
Foundation already built in a prior sprint
(`app/models/dataset_governance.py`, `docs/ml-governance/DATASET_REGISTRY.md`)
rather than duplicating it.

## Filesystem structure

`/dataset` at the repository root — see `/dataset/README.md` and each
subfolder's own README for exactly what belongs there. The database
(below) is the system of record; the filesystem holds real image bytes,
generated exports, and validation reports.

## Permanent Dataset ID

Every registered image receives a permanent `LCID-YYYY-NNNNNNNNN`
identifier (`DatasetRegistryEntry.lcid`), generated once by
`app.services.ml.lcid_service.generate_lcid()` from a dedicated per-year
atomic counter (`LcidSequenceCounter`) — never derived from row count, so
archiving or excluding an entry never causes an ID collision or reuse. The
ID never changes; an archived entry keeps its LCID forever.

## Required per-image metadata

`DatasetRegistryEntry` tracks every field Section 3 requires as a real
column (not a JSON blob): Dataset ID (`lcid`), Inspection ID, capture date,
capture device, instrument family/model, manufacturer, anatomy zone,
lighting, resolution, image quality, reviewer status, Ground Truth status
(via the annotation lifecycle), Digital Twin ID, baseline ID, usage
rights, and dataset version. Registration is refused
(`MetadataValidationError`) if `instrument_family`, `manufacturer`,
`facility`, `operator`, `capture_device`, or `image_resolution` is blank —
see `app.services.ml.dataset_registry.REQUIRED_STRING_FIELDS`.

## No training outside this registry

`app.services.ml.dataset_builder.eligible_entries()` is the only sanctioned
path from the registry to a trainable sample set, and it excludes archived
entries, `Reject`-quality images, PHI-unverified images, and anything not
explicitly marked `training_eligibility=True` and `APPROVED`. The existing
candidate training pipeline (`app.services.ml.candidate_training`) only
ever consumes this filtered set.

## See also

`DATASET_CARD.md`, `LABEL_GUIDE.md`, `ANNOTATION_GUIDE.md`,
`REVIEW_GUIDE.md`, `IMAGE_QUALITY_GUIDE.md`, `GROUND_TRUTH_GUIDE.md`,
`UNKNOWN_FINDING_GUIDE.md`, `DIGITAL_TWIN_LINKAGE.md`,
`DATASET_VERSIONING.md` — all under `docs/lcid/`.
