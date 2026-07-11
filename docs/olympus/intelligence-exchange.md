# Project Olympus — Global Intelligence Exchange & Healthcare Intelligence
Exchange (HIX)

LumenAI OS v5.1, Sections 3 & 4.

## One package model, references content, never copies it

`HIXExchangePackage` never duplicates the underlying content. It carries
`content_ref_type`/`content_ref_id` pointing at the real row (a
`KnowledgeArticle`, a `WorkflowDefinition`, a Digital Twin model snapshot
id, ...) and only owns the exchange's own governance and de-identification
state. `package_type` covers every content category both sections name:
knowledge packages, workflow templates, Digital Twin models, inspection
protocols, educational modules, benchmark reports, anatomy models,
contamination trends, quality insights, and research findings.

## Every contribution requires governance approval

A package's lifecycle is strict: `draft` → `pending_governance_review` →
(`approved` | `rejected`) → `published`. It is impossible to reach
`published` without an explicit `approved` governance decision recorded
first — `publish_package` raises `InvalidPackageStateError` otherwise.
Submission itself requires both `no_phi_confirmed` and
`no_identifiable_customer_data_confirmed` to be true.

## De-identification

Follows the exact pattern already established by
`horizon_contribution_service.py`: `source_tenant_id` and `submitted_by`
are included in a package's representation only when the requesting
tenant *is* the source. Every other reader of the published, network-wide
exchange (`GET /exchange/packages`) sees a de-identified package with no
hospital identity attached.

## Every exchange action is audited

`submit_package`, `governance_review_package`, and `publish_package` each
call `enterprise_audit_service.record_enterprise_audit_event` directly —
the current, hash-chained, tamper-evident audit writer — never the
deprecated `app.audit.log_audit_event`.

```
POST /api/olympus/exchange/packages
POST /api/olympus/exchange/packages/{id}/governance-review
POST /api/olympus/exchange/packages/{id}/publish
GET  /api/olympus/exchange/packages/{id}
GET  /api/olympus/exchange/packages?package_type=knowledge_package
GET  /api/olympus/exchange/packages/mine
```
