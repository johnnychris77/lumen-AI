# Project Sage — Education and Competency Agent

LumenAI AI Specialist, Mission & Section 1.

## What Sage does

Sage converts validated inspection findings, supervisor feedback, process
trends, instrument failures, and institutional knowledge into targeted
workforce-development recommendations. It determines what knowledge gap may
exist, which competency is affected, who may need education, which
instrument or anatomy zone should be taught, what validated evidence
supports the education, and whether education improved future performance.

Sage supports technicians, supervisors, educators, and SPD leaders. It does
**not** discipline employees, independently determine competency, or replace
supervisor and educator judgment.

## Architecture position

```
Inspection Findings -> Supervisor Validation -> Aegis Process Intelligence ->
Vulcan Reliability Intelligence -> Knowledge Graph -> Competency Gap Analysis
-> Targeted Education -> Human Assignment and Approval -> Effectiveness
Measurement -> Institutional Learning
```

## Deterministic, not an autonomous LLM

Sage is a deterministic Python orchestrator composing real, already-recorded
signal. There is no LLM/embedding API call anywhere in Sage.

## What is reused vs. genuinely new

Sage does not build a parallel competency store. It composes:

- `CompetencyEvent` (`app/models/competency_event.py`) via
  `competency_service.py` -- the existing per-technician event log
  (finding_reviewed / supervisor_correction / repeated_error /
  education_completed / annual_competency / procedure_validation /
  simulation_passed / simulation_failed / knowledge_contribution).
- `SupervisorReview` (`app/models/supervisor_review.py`) -- the ML
  ground-truth label store, joined to `Inspection.technician` -- Sage's real
  evidence for gap detection.
- `Inspection.coverage_pct` / `Inspection.ai_confidence` -- real,
  already-persisted per-inspection fields.
- `education_library.get_article` / `clinical_mentor.FINDING_EDUCATION` --
  the platform's one approved-content source for microlearning.
- `athena_memory_service.list_memory_entries` -- Athena's institutional
  knowledge composition, called through rather than re-queried.
- `apollo_quality_twin_service.twin_history` -- Apollo's competency/education
  scores, read-only.
- `RetainedImage`/`ImageLabel` (`app/models/retained_image.py`) -- the real,
  governed image store, curated (not duplicated) for education use.
- `vulcan_aegis_integration_service.compute_process_variation_signal` and
  `VulcanReliabilityAssessment` -- read, never overwritten.

Genuinely new: seven tables (`SageKnowledgeGap`, `SageLearningPlan`,
`SageMicrolearningModule`, `SageAssessment`, `SageEducationImageEntry`,
`SageEffectivenessAssessment`, `SageFeedback`) and fifteen service modules.

## Responsibilities (Section 1)

- identify recurring knowledge gaps
- identify repeated anatomy-zone errors
- identify inspection coverage weaknesses
- identify image-capture quality issues
- recommend targeted education
- recommend competency reassessment
- create education drafts
- link education to findings and evidence
- measure post-education performance
- capture supervisor and educator feedback

Every recommendation includes evidence, confidence, and a human approval
requirement (`human_review_required = True` on every new table).

## API

```
POST /api/sage/gaps/detect/{technician}
GET  /api/sage/gaps
```

See `docs/agents/sage/competency-gap-detection.md`,
`docs/agents/sage/adaptive-learning-plans.md`, and
`docs/agents/sage/learning-effectiveness.md` for the full pipeline.
