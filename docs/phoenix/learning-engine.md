# Project Phoenix — Learning Engine

LumenAI OS v4.9, Section 1.

## Naming disambiguation

Phoenix is the 18th additive sprint. Every existing performance/
analytics-adjacent system was read in full before writing any code:

| Concern | Pre-existing system | Phoenix's relationship to it |
|---|---|---|
| Precision/recall/F1/FP-FN/agreement | `ml/pilot_validation.py::clinical_metrics` | Composed directly in `phoenix_ai_observatory_service.py` |
| Model drift | `sentinel_ai_health_service.compute_ai_health` | Composed directly |
| Duplicate/outdated/emerging knowledge | `athena_curator_service.py` (v4.8) | Composed directly; only "contradictory guidance" is new |
| Coaching/team-education opportunities | `competency_intelligence_service.py` (v2.9) | Composed directly; 5 new detector types added to the same `CompetencyOpportunity` model |
| Quality Maturity Index | `apollo_quality_twin_service.py` (v4.7) | Reused as the "Quality" input dimension of Phoenix's own 9-dimension index |
| Multi-step approval | `WorkflowApprovalChain`/`WorkflowApprovalInstance` (Forge, v4.1) | Reused directly for Continuous Validation — no second approval-chain model |
| Executive rollups | `vanguard_executive_intelligence_service`/`vanguard_governance_service` (v4.6) | Composed for "enterprise trends" and the "Executive Intelligence" maturity dimension |

`/api/phoenix` and the frontend routes `/phoenix`/`/platform-health` were
confirmed free.

## The Learning Engine

`phoenix_learning_engine_service.learning_engine_summary` composes eight
real, continuously-updated signals — no re-derivation of any of them:

* Inspection outcomes — `quality_command_center_service` (quality events, recurring findings, CAPAs)
* AI confidence — `phoenix_ai_observatory_service` (confidence average, calibration, drift)
* Supervisor overrides — the same observatory's override/agreement rates
* Knowledge usage — `knowledge_analytics_service` (most-viewed articles, common questions, gaps)
* Workflow efficiency — `phoenix_workflow_optimization_service`
* Digital Twin health — `digital_twin_engine` (instrument-flow twin, via Platform Health's scoring)
* Enterprise trends — `vanguard_executive_intelligence_service`
* Education effectiveness — `quality_command_center_service`'s education-impact figures

```
GET /api/phoenix/learning-engine/summary
```

## Never modifies production automatically

Every Phoenix output that could inform a change — a recommendation, a
workflow-optimization suggestion, a competency opportunity — is read-only
decision support. The only way a recommendation moves forward is through
an explicit human decision recorded via the Continuous Validation
pipeline (`docs/phoenix/improvement-engine.md`).

## Tenant authorization

Like Athena (v4.8), every Phoenix route uses `tenant_authz.
require_tenant_roles` (real `TenantMembership` verification) — Phoenix is
a new module and does not knowingly reintroduce the header-only
cross-tenant gap the first 16 modules still carry.
