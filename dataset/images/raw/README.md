# images/raw/

Freshly captured or ingested images that have not yet been quality-graded,
de-identified, or reviewed. Nothing here is eligible for annotation,
training, or export. An image moves out of `raw/` once
`app.services.ml.image_quality` has produced a real
`ImageQualityAssessment` and EXIF stripping/de-identification has run
(mirroring the existing `RetainedImage.exif_stripped` guarantee).
