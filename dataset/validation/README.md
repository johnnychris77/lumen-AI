# validation/

Dataset governance validation reports produced by
`app.services.ml.dataset_validation_service.validate_registry()`: duplicate
images, missing metadata, invalid labels, invalid reviewer status, orphaned
Digital Twin links, missing baseline links, missing usage rights, and
duplicate LCIDs. Distinct from
`app.services.ml.dataset_integrity` (a pre-training sample-list check run
just before a train/validation/test split) — this is a whole-registry
hygiene sweep, run independently of any training pipeline.
