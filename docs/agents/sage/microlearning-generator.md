# Project Sage — Microlearning Generator

LumenAI AI Specialist, Section 6.

## Only approved sources

`sage_microlearning_service.build_module_from_finding` generates a module
*only* from `education_library.get_article` (itself built from
`clinical_mentor.FINDING_EDUCATION` + `instrument_anatomy.py` + the IFU
reference note) — the platform's one approved-content library, covering 12
contamination/condition categories (`education_library.CATEGORIES`).

A `finding_type` outside that library returns `None` — Sage refuses to
author unsupported clinical guidance rather than fabricate a module.

## Module fields (Section 6)

Learning objective, why it matters, anatomy overview, common findings,
inspection steps, corrective actions, knowledge check, source references,
and approval status — all real columns on `SageMicrolearningModule`,
populated directly from the approved article, never invented text.

## Approval workflow

Every module starts `approval_status = "draft"`. `POST
/api/sage/microlearning/{id}/approve` is required before a module appears in
`GET /api/sage/microlearning?approval_status=approved` (the default view
used by the Sage Workspace and Technician Learning Center).

## API

```
POST /api/sage/microlearning/{finding_type}
POST /api/sage/microlearning/{module_id}/approve
GET  /api/sage/microlearning
```
