# LumenAI Clinical Image Dataset (LCID)

This directory is the governed root of the LumenAI Clinical Image Dataset —
the single, versioned, auditable location for every image and export this
program's computer-vision work draws from. **This directory does not
itself train a model.** It is the governed foundation every future model
must be built on, per `docs/lcid/DATASET_SPECIFICATION.md`.

No AI model may be trained on data outside this governed structure, and no
image may enter `approved/` without passing through the review workflow
described in `docs/lcid/REVIEW_GUIDE.md`.

## Layout

| Path | Purpose |
|---|---|
| `images/raw/` | Freshly captured/ingested images, not yet quality-graded or reviewed |
| `images/processed/` | EXIF-stripped, de-identified images ready for annotation |
| `images/rejected/` | Images that failed image-quality grading (`Reject`) — retained, searchable, never trainable |
| `images/approved/` | Images with Approved Ground Truth — the only images eligible for training export |
| `metadata/` | Per-image metadata records mirroring the `DatasetRegistryEntry` schema |
| `annotations/` | Annotation/review event exports (mirrors `AnnotationEvent`/`DoubleBlindReview`) |
| `exports/` | Generated training-format exports (classification/object_detection/segmentation/multi_label) |
| `validation/` | Dataset validation reports (`dataset_validation_service.validate_registry`) |
| `baseline/` | Baseline-linkage references for images compared against an approved baseline |
| `models/` | Model-training-run artifacts that consumed a specific dataset version |
| `docs/` | Human-readable copies/exports of the governance docs under `docs/lcid/` |

## Real vs. placeholder content

The database tables (`DatasetVersion`, `DatasetRegistryEntry`,
`AnnotationEvent`, `DoubleBlindReview`, `ImageQualityAssessment`,
`LcidSequenceCounter` — `backend/app/models/dataset_governance.py`) are the
system of record. This filesystem tree is where real image bytes,
generated exports, and validation reports are written by the services in
`backend/app/services/ml/` — it is not a separate, disconnected copy of the
data.
