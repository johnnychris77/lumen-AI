# Project GuardianX — Model Governance & Governance Workflow

LumenAI Network v5.2, Sections 2 & 6.

## Model Governance (Section 2) — extends Olympus's registry, no new table

Olympus's `AIModelRegistryEntry` (v5.1) already tracks
`validation_status`/`clinical_scope`/`evidence_json`/
`performance_metrics_json`/certification. GuardianX adds the fields
Section 2 names directly onto that same table: `model_owner`,
`clinical_owner`, `technical_owner`, `approval_committee`,
`validation_date`, `retirement_date`,
`training_dataset_metadata_json`, `known_limitations`,
`approved_use_cases_json`, `out_of_scope_uses_json`.

```
PATCH /api/guardianx/models/{id}/ownership
POST  /api/guardianx/models/{id}/validation-date
POST  /api/guardianx/models/{id}/retire
PATCH /api/guardianx/models/{id}/training-dataset-metadata
PATCH /api/guardianx/models/{id}/known-limitations
PATCH /api/guardianx/models/{id}/use-cases
GET   /api/guardianx/models/{id}/governance
GET   /api/guardianx/models/governance
```

## Governance Workflow (Section 6) — Forge's approval chain, fifth reuse

"Every production model requires documented approval." GuardianX reuses
Forge's `WorkflowApprovalChain`/`WorkflowApprovalInstance`
(`forge_approval_service.py`, v4.1) for the **fifth** time — after
Athena, Phoenix, Infinity, and Olympus's certification chain — with five
named gates:

```
Clinical Review Board → AI Governance Committee → Quality Leadership → Security → Compliance
```

This is a **second, distinct** approval chain per model, linked via new
`governance_chain_id`/`governance_instance_id`/`governance_status`
columns — separate from Olympus's `certification_chain_id`/
`certification_status` (Section 7 of Olympus, the 7 certification
gates). A model can be certified without governance sign-off, or vice
versa; `guardianx_governance_workflow_service.is_production_ready`
checks `governance_status == "approved"` specifically, never
certification status.

```
POST /api/guardianx/models/{id}/governance-review/start
POST /api/guardianx/models/{id}/governance-review/advance
GET  /api/guardianx/models/{id}/governance-review
```

A rejection at any gate ends the review immediately (Forge's existing
`decide_step` behavior) — `governance_status` becomes `rejected`, and it
can never reach `approved` without an explicit approval recorded at
every one of the five gates.

## AI Risk Registry (Section 5)

`AIModelRiskEntry` is a many-rows-per-model table — a model typically
has several distinct risks — with a `risk_type` discriminator (`bias`,
`failure_mode`, `clinical_boundary`, `general_risk`), a severity
(`low`/`medium`/`high`/`critical`), and a lifecycle status
(`open`/`mitigated`/`accepted`). Distinct from the single-value
`approved_use_cases_json`/`out_of_scope_uses_json` scope declarations
above — a risk describes *why* a use might be dangerous; a scope
declaration describes *which* uses are approved at all.

```
POST  /api/guardianx/risks
PATCH /api/guardianx/risks/{id}/status
GET   /api/guardianx/models/{id}/risks
GET   /api/guardianx/risks/summary
```
