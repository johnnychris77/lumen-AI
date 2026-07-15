# Annotation Workspace — Project Canvas

**Status:** The user-facing workspace for ingesting, annotating, reviewing,
adjudicating, and releasing real borescope images. Every capability here is
a UI/route layer over infrastructure that already existed before this
sprint (`docs/annotation-database/`, `docs/lcid/`) — this sprint adds no
second annotation model, dataset registry, review workflow, baseline
concept, Digital Twin identity, or model-training mechanism.

## Composition, not duplication

| This sprint adds | Reuses (unchanged) |
|---|---|
| `app/routes/dataset_ingestion.py`, `app/services/dataset_ingestion_service.py` | `image_retention_service.retain_image()`, `dataset_registry.register_image()`/`find_duplicate()` |
| `app/routes/reviewer_queues.py`, `app/services/reviewer_queue_service.py` | `annotation_review_service.*`, `annotation_ground_truth_service.is_eligible_for_ground_truth()` |
| `app/routes/dataset_eligibility.py`, `app/services/dataset_eligibility_service.py` | `dataset_registry` governance columns, `dataset_builder.eligible_entries()` gates |
| `app/routes/review_workspace.py` (blind secondary view, baseline comparison) | `annotation_review_service`, `lcid_service.resolve_baseline_id()` |
| `app/routes/dataset_release.py` (release preview, export preview) | `dataset_builder`, `dataset_split`, `annotation_export_service.export_annotations()` |
| `GET /annotations/{id}/review` (added to `app/routes/annotation_database.py`) | `annotation_review_service.get_review()` |

## Frontend routes

| Route | Page | Role gate |
|---|---|---|
| `/dataset/images` | `DatasetImageLibraryPage.tsx` | Viewer+ |
| `/dataset/images/upload` | `DatasetImageUploadPage.tsx` | Annotator+ |
| `/dataset/images/:imageId` | `DatasetImageDetailPage.tsx` | Viewer+ |
| `/annotations` | `AnnotationsListPage.tsx` | Viewer+ |
| `/annotations/:annotationId` | `AnnotationDetailPage.tsx` | Viewer+ |
| `/review/primary` | `PrimaryReviewWorkspacePage.tsx` | Reviewer+ |
| `/review/secondary` | `SecondaryReviewWorkspacePage.tsx` | Reviewer+ |
| `/review/disagreements` | `DisagreementQueuePage.tsx` | Reviewer+ |
| `/review/adjudication` | `AdjudicationWorkspacePage.tsx` | Clinical Reviewer/Admin |
| `/ground-truth` | `GroundTruthWorkspacePage.tsx` | Reviewer+ |
| `/dataset/releases` | `DatasetReleaseBuilderPage.tsx` | Admin/AI Researcher |

Client-side `RequireRole` gates are a UX convenience only — every route
above is independently enforced by the backend (`ROLES_MAY_ANNOTATE`,
`ROLES_MAY_REVIEW`, `ROLES_MAY_FINALIZE_GROUND_TRUTH`, `ROLES_MAY_EXPORT`,
`ROLES_MAY_VIEW` in `app/models/annotation_database.py`).

## Role mapping (free-form `String` role column → UI role)

| Backend role | Workspace role |
|---|---|
| `admin` | Administrator |
| `clinical_reviewer` | Clinical Reviewer |
| `spd_manager` | Reviewer |
| `operator` | Annotator |
| `ai_researcher` | AI Researcher |
| `viewer` | Viewer |

## See also

`IMAGE_INGESTION_GUIDE.md`, `BULK_UPLOAD_GUIDE.md`,
`PRIMARY_REVIEW_GUIDE.md`, `SECONDARY_BLIND_REVIEW_GUIDE.md`,
`ADJUDICATION_WORKSPACE_GUIDE.md`, `GROUND_TRUTH_WORKSPACE_GUIDE.md`,
`BASELINE_COMPARISON_GUIDE.md`, `DATASET_RELEASE_BUILDER.md`,
`MANUAL_ACCEPTANCE_TEST.md`, and the pre-existing `docs/annotation-database/`
and `docs/lcid/` guides this sprint composes with.
