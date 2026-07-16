# metadata/

Per-image metadata mirroring `app.models.dataset_governance.DatasetRegistryEntry`
— Dataset ID (LCID), Inspection ID, capture metadata, instrument/manufacturer,
anatomy zone, image quality, reviewer status, Ground Truth status, Digital
Twin ID, baseline ID, usage rights, and dataset version. No image may be
registered without the required fields in
`app.services.ml.dataset_registry.REQUIRED_STRING_FIELDS` — see
`docs/lcid/DATASET_SPECIFICATION.md`.
