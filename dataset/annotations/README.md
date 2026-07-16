# annotations/

Annotation lifecycle records — the append-only event log
(`app.models.dataset_governance.AnnotationEvent`) and double-blind review
records (`DoubleBlindReview`: primary reviewer, independent reviewer,
agreement, adjudicator). See `docs/lcid/REVIEW_GUIDE.md` for the full
UNREVIEWED → PRIMARY REVIEW → SECOND REVIEW → DISAGREEMENT → ADJUDICATION →
APPROVED → ARCHIVED workflow and how it maps onto the codebase's existing
`UNLABELED`/`LABELED`/... state names.
