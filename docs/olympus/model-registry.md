# Project Olympus — AI Model Registry & Certification Registry

LumenAI OS v5.1, Sections 6 & 7.

## AI Model Registry (Section 6) — genuinely new

Nothing in this codebase tracks an AI model as a first-class, versioned
registry object. Sentinel's AI health service reports live operational
health; Phoenix's `AIInferenceLatencySample` is a performance sample, not
a model identity. `AIModelRegistryEntry` covers the four named model
types (vision, reasoning, knowledge, simulation) with version, validation
status, clinical scope, evidence, and performance metrics.

`supersedes_id` is a nullable self-FK forming a real version chain —
the same pattern already used by `QualityPolicy` (Apollo) and
`StandardsPublication` (P24). `version_chain` walks it oldest-first.

```
POST  /api/olympus/models
GET   /api/olympus/models?model_type=vision&validation_status=validated
GET   /api/olympus/models/{id}
PATCH /api/olympus/models/{id}/validation-status
GET   /api/olympus/models/{id}/version-chain
```

## Certification Registry (Section 7) — not a new certification engine

A read-only index across two surfaces that already certify things through
Forge's `WorkflowApprovalChain` (`forge_approval_service.py`, reused here
for the **fourth** time after Athena, Phoenix, and Infinity):

* Infinity's `MarketplaceListing.certification_status` — workflows,
  knowledge, and education content published as marketplace listings.
* This sprint's `AIModelRegistryEntry.certification_status` — AI models,
  certified through the same 7-gate `CERTIFICATION_GATES` Infinity
  already defined (Security → Performance → Clinical Safety →
  Explainability → Accessibility → Documentation → Governance), for
  consistency across both certification surfaces.

```
POST /api/olympus/models/{id}/certification/start
POST /api/olympus/models/{id}/certification/advance
GET  /api/olympus/models/{id}/certification
GET  /api/olympus/certification-registry
```

`GET /api/olympus/certification-registry` is "certification status is
visible to participants" (Section 7's requirement) — a single view
listing every certified/in-progress/rejected marketplace listing and AI
model, with running totals.
