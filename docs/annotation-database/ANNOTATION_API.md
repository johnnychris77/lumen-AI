# Annotation Database API

All routes in `backend/app/routes/annotation_database.py`, mounted under
the standard `settings.API_PREFIX` (`/api`).

| Route | Method | Role gate | Purpose |
|---|---|---|---|
| `/annotations` | POST | Annotator+ | Create an annotation |
| `/annotations` | GET | Viewer+ | List (filterable by `retained_image_id`, `ground_truth_status`) |
| `/annotations/{id}` | GET | Viewer+ | Fetch one |
| `/annotations/{id}/versions` | GET | Viewer+ | Full version history |
| `/annotations/{id}` | PATCH | Annotator+ | Update — requires a `reason`; creates a new version |
| `/annotations/{id}/review/primary` | POST | Reviewer+ | Submit primary review |
| `/annotations/{id}/review/secondary` | POST | Reviewer+ | Submit independent secondary review (blind) |
| `/annotations/{id}/review/adjudicate` | POST | Clinical Reviewer/Admin | Resolve a disagreement |
| `/annotations/{id}/promote-ground-truth` | POST | Clinical Reviewer/Admin | Finalize Ground Truth — see `GROUND_TRUTH_MODEL.md` |
| `/annotations/analytics/summary` | GET | Viewer+ | All Section 11 analytics in one response |
| `/annotations/export` | POST | Admin/AI Researcher | Export — see below |

"Annotator+"/"Reviewer+" means that role and every role above it in
`REVIEWER_WORKFLOW.md`'s hierarchy also passes.

## Export formats

`classification`, `yolo`, `coco`, `pascal_voc`, `segmentation`, `csv`,
`json` — see `annotation_export_service.EXPORT_FORMATS`. Defaults to
`ground_truth_only=True`; pass `false` explicitly to export draft
annotations (e.g. for internal QA), never for a training manifest.
