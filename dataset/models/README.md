# models/

Model-training-run artifacts that consumed a specific, frozen dataset
version (`app.models.dataset_governance.DatasetVersion`). This sprint does
not train a model — see `docs/lcid/DATASET_VERSIONING.md` — but any future
training run must record here which frozen dataset version (e.g. `v1.0`)
it was built from, so a model's provenance is always traceable back to an
immutable dataset snapshot. Reuses the existing training pipeline in
`app.services.ml.candidate_training` rather than a new one.
