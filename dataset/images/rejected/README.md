# images/rejected/

Images graded `Reject` by the image-quality engine
(`app.models.dataset_governance.QUALITY_REJECT`). These remain here
permanently for traceability and are searchable via the dataset registry,
but per Section 4 of the LCID spec they can **never** enter a training
export — `app.services.ml.dataset_builder.eligible_entries` excludes any
entry whose `image_quality == QUALITY_REJECT` unconditionally.
