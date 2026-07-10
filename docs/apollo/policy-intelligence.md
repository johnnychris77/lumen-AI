# Project Apollo — Policy Intelligence & Continuous Improvement Portfolio

LumenAI OS v4.7, Sections 6 & 8.

## Policy Intelligence (Section 6)

`QualityPolicy` (table `apollo_quality_policies`) is a genuinely new table
— no clinical/quality policy versioning system existed before Apollo
(`RetentionPolicy`/`GovernanceSlaPolicy` are unrelated infrastructure
policies). It follows the same `supersedes_id`/`status` self-FK chain
Beacon's `StandardsPublication` and Forge's `WorkflowDefinition` already
established, including the identical version-chain-walk pattern used by
`beacon_standards_service.version_history`.

Every policy tracks:

* Review date (`review_date`) — the basis for `policies_due_for_review`.
* Owner (`owner`).
* References (`references_json`).
* Linked standards (`linked_standards_json`).
* Affected workflows (`affected_workflows_json`).
* Affected competencies (`affected_competencies_json`).
* Affected AI rules (`affected_ai_rules_json`).

Publishing a new version (`POST /policies/{id}/publish` with a
`supersedes_id`) automatically marks the prior published version
`superseded` — mirroring Beacon's `publish_guidance`.

```
POST  /api/apollo/policies
GET   /api/apollo/policies
GET   /api/apollo/policies/{id}
POST  /api/apollo/policies/{id}/publish
GET   /api/apollo/policies/{id}/history
GET   /api/apollo/policies/due-for-review?within_days=30
```

## Continuous Improvement Portfolio (Section 8)

`ContinuousImprovementInitiative` (v1.5) already tracked named PI/Lean/Six
Sigma/Kaizen initiatives from proposal through completion. Apollo adds
additive columns rather than a new table:

* `methodology` — one of `pi | lean | six_sigma | kaizen | other`.
* `cost_savings_usd` — human-entered, never computed.
* `quality_improvement_metric` / `risk_reduction_metric` — free-text,
  human-entered, matching the existing `actual_impact` pattern (a
  before/after delta requires human judgment about what changed and why,
  not a raw metric diff).
* `executive_visible` — flags a project for the Executive Quality
  Dashboard's continuous-improvement tile.

```
POST   /api/apollo/improvement-projects
GET    /api/apollo/improvement-projects
GET    /api/apollo/improvement-projects/summary
PATCH  /api/apollo/improvement-projects/{id}
```

`improvement-projects/summary` rolls up counts by methodology/status,
total (human-entered) cost savings, and the completion rate used as an
input to the Quality Maturity Index (see `quality-digital-twin.md`).
