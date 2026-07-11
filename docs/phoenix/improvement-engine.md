# Project Phoenix — Improvement Recommendation Engine & Continuous Validation

LumenAI OS v4.9, Sections 2, 3, 4, 6 & 9.

## Improvement Recommendation Engine (Section 2)

`phoenix_recommendation_engine.generate_recommendations` scans the real
outputs of every other Phoenix engine and drafts an
`ImprovementRecommendation` for each genuine signal found:

| Trigger | Real signal | Recommendation type |
|---|---|---|
| AI health drift detected | `sentinel_ai_health_service._detect_drift` (via the AI Observatory) | `review_ai_confidence` |
| Low-confidence anatomy zone | `ml/pilot_validation.zone_performance`'s `lowest_confidence_zones` | `collect_baseline_images` |
| High-miss-rate anatomy zone | `zone_performance`'s `highest_risk_zones` | `improve_anatomy_model` |
| Documented knowledge gap | Knowledge Evolution Center | `revise_inspection_guidance` |
| Contradictory guidance | Knowledge Evolution Center | `update_sop` |
| Duplicate/retirement candidates | Knowledge Evolution Center | `improve_knowledge_graph` |
| Open coaching/education opportunities | Competency Intelligence | `create_competency` |
| Repeated workflow execution failures | Workflow Optimization Engine | `update_workflow` |

Every recommendation carries **Evidence** (the exact real records that
triggered it), **Expected Benefit**, **Confidence** (0-1), **Impact
Assessment**, and **Required Approvals** (role names). A recommendation
starts as `draft` and never auto-enters Continuous Validation.

```
POST /api/phoenix/recommendations/generate
GET  /api/phoenix/recommendations?status=draft
GET  /api/phoenix/recommendations/{id}
```

## AI Performance Observatory (Section 3)

See `docs/phoenix/learning-engine.md`'s disambiguation table.
`phoenix_ai_observatory_service.py` adds two genuinely new metrics on top
of the composed `clinical_metrics`/`compute_ai_health` figures:

* **Inference Latency** — real, explicitly recorded samples
  (`AIInferenceLatencySample`); reports "insufficient data" rather than a
  fabricated typical value when none exist.
* **Coverage** — "% of inspections that received a real AI confidence
  score," a different concept from `inspection_coverage.py`'s image/zone
  capture-completeness metric of the same name.

```
GET  /api/phoenix/observatory/summary
POST /api/phoenix/observatory/latency
GET  /api/phoenix/observatory/latency
GET  /api/phoenix/observatory/coverage
```

## Workflow Optimization Engine (Section 4)

`WorkflowExecution` already records real `execution_time_ms`, but no
duration/bottleneck/queue-delay/rule-complexity analytics existed over it
before Phoenix. `phoenix_workflow_optimization_service.py` reads these
rows directly:

* **Duration analysis** — avg/min/max `execution_time_ms`, grouped by status.
* **Approval bottlenecks** — `WorkflowApprovalInstance` rows pending longer than a threshold.
* **Repeated exceptions** — workflows with recurring failed executions.
* **Rule complexity** — a real recursive node-count of each `WorkflowRule`'s nested condition tree.

Recommending an optimized workflow "through Project Forge" (the brief's
own words) means the recommendation names the real `WorkflowDefinition`
and cites this evidence — it never calls `forge_workflow_service.
revise_workflow` itself.

```
GET /api/phoenix/workflow-optimization/summary
GET /api/phoenix/workflow-optimization/{workflow_id}
```

## Competency Intelligence (Section 6)

See `docs/phoenix/learning-engine.md` — extends `competency_intelligence_
service.py` with detectors for the two previously-unused `annual_
competency`/`recurring_learning` types plus three new types (`simulation`,
`mentoring`, `knowledge_sharing`), all on the same `CompetencyOpportunity`
table.

```
POST /api/phoenix/competency-intelligence/run
GET  /api/phoenix/competency-intelligence/opportunities
```

## Continuous Validation (Section 9)

Every recommendation moves through:

```
Review → Clinical Validation → Technical Review → Pilot → Measurement → Production
```

Rather than a second approval-chain model, this reuses Project Forge's
existing `WorkflowApprovalChain`/`WorkflowApprovalInstance`
(`forge_approval_service.py`, v4.1) directly — one chain per
recommendation, with these six stages as its ordered steps. A rejection
at any stage ends the pipeline immediately (Forge's existing behavior);
`ValidationOutcome` rows track outcomes and lessons learned at each stage.

```
POST /api/phoenix/recommendations/{id}/validation/start
POST /api/phoenix/recommendations/{id}/validation/advance
POST /api/phoenix/recommendations/{id}/validation/outcomes
GET  /api/phoenix/recommendations/{id}/validation
```

No recommendation reaches `production` without an explicit human approval
recorded at every one of the six stages.
