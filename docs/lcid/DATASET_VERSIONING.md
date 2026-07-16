# LCID Dataset Versioning

## Immutable versions

`app.models.dataset_governance.DatasetVersion` is the first-class,
immutable versioning entity (e.g. `LCID v0.1`, `LCID v0.2`, `LCID v1.0` as
`version_label` values). `app.services.ml.dataset_registry.freeze_dataset_version()`
makes a version permanently immutable — once frozen, no new image may be
registered into it and `image_count_at_freeze` is recorded as a permanent
snapshot count. A correction after freezing requires a **new** version
referencing the old one via `supersedes_id`, never a silent edit of a
frozen version's contents.

## Export and training always reference a version

Every export (`dataset_export_service.export_dataset()`) and every
training run (`dataset_builder.build_training_dataset()`,
`candidate_training.run_full_candidate_pipeline()`) takes an explicit
`dataset_version_id` — there is no "current dataset" global default that
could silently drift underneath a running experiment.

## Provenance

`/dataset/models/README.md` records the expectation that any future
training run documents which frozen dataset version it consumed —
traceability from a trained model back to an immutable dataset snapshot,
per this sprint's Definition of Done.
