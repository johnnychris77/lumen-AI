# exports/

Generated training-format exports written by
`app.services.ml.dataset_export_service.export_dataset()`:
`dataset_v{version_id}_{format}.json` for `classification`,
`object_detection`, `segmentation`, and `multi_label`. Every export
preserves the full metadata record for each included image.

**Honesty note**: `object_detection` and `segmentation` exports include
the fields those formats expect (`bounding_boxes`/`masks`) but leave them
empty with `"annotation_available": false` — no bounding-box or pixel-mask
annotation tool exists in this codebase yet, so nothing is fabricated.
