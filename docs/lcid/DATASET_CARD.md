# LCID Dataset Card

Modeled on the existing model-card discipline
(`docs/ml-governance/MODEL_CARD_TEMPLATE.md`) applied to the dataset
itself rather than a trained model.

## What this dataset is

A governed registry of sterile-processing instrument inspection images,
each carrying full capture/instrument/facility metadata, a review/Ground
Truth lifecycle, an image-quality grade, and (where known) Digital Twin and
baseline linkage. Composed of real `RetainedImage` bytes referenced by
`DatasetRegistryEntry` rows — never a second copy of the image data.

## What this dataset is not

- Not a diagnostic or clinically validated dataset — every image reflects
  a probability-based visual observation per
  `docs/decision-engine/RECOMMENDATION_LANGUAGE_STANDARD.md`, never a
  laboratory-confirmed finding.
- Not a released, versioned training set until a `DatasetVersion` is
  explicitly frozen (`DATASET_VERSIONING.md`).
- Not de-identified by this document's say-so alone — de-identification is
  a real, enforced property of `RetainedImage.exif_stripped` and
  `consent_recorded`, verified at ingestion, not assumed here.

## Composition (reported, not fabricated)

Composition (facility count, manufacturer count, instrument-family count,
label distribution) is computed live by
`app.services.ml.dataset_builder.balance_report()` — this card intentionally
does not hardcode a snapshot number that would go stale; query the live
registry (`GET /api/dataset-registry/images`) for current counts.

## Known limitations

- No bounding-box or pixel-mask annotation tool exists yet — see
  `DATASET_SPECIFICATION.md`'s note on `object_detection`/`segmentation`
  exports.
- Digital Twin linkage is only as good as the underlying barcode/UDI
  capture — an instrument with no captured identifier is honestly reported
  as `untracked:...`, never fabricated as re-identified.
