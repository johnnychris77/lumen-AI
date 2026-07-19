# LPR-DIR-012 — System Inventory

**Basis:** implemented code at `c9797b2`. Classification per the required scale:
Implemented / Partially Implemented / Documented Only / Placeholder / Deprecated /
Missing / Future. Owners are **role-based** (see `MODULE_OWNERSHIP_MATRIX.md`).
Readiness detail is in `MODULE_READINESS_SCORECARD.md`.

This inventory is organized by the directive's categories. For each component:
purpose, source, classification, auth/tenant/audit requirement, failure behavior,
tests, owner, lifecycle, readiness, known gaps.

## Platform layers

| Component | Source | Class | Auth/Tenant/Audit | Failure behavior | Owner | Readiness |
|---|---|---|---|---|---|---|
| Frontend SPA | `frontend/` | Implemented | Session via API; no direct DB | Degraded UI; safe states | Frontend Eng | READY w/ conditions |
| Backend API runtime | `backend/app/main.py` + routes | Implemented | Typed principal on protected paths | Fail-closed | Backend Eng | READY |
| API Gateway (routing+deps) | `app.main`, auth deps | Implemented | Enforced pre-service | 401/403 fail-closed | Backend/Security Eng | READY |
| Database (ORM) | `app.db`, models | Implemented | Tenant-scoped columns | `/ready` DB hard-gate | Data Eng | READY |
| Object/file storage | foundation object storage svc | Implemented | Access-controlled | Integrity-hashed access | Infra Eng | READY w/ conditions |
| Configuration | env + `alembic.ini` + settings | Implemented | Secrets not in code | Startup fails closed | Platform Eng | READY |
| Deployment | Dockerfile, compose, helm/k8s, render | Implemented | N/A | Container restart | Infra Eng | READY w/ conditions |
| Monitoring/Logging | `observability/`, foundation MONITORING | Implemented | Audit-linked | Alerts | Infra Eng | READY w/ conditions |
| Notification | notification services | Implemented | Tenant-scoped | Retry/queue | Backend Eng | READY w/ conditions |

## Security & identity

| Component | Source | Class | Notes | Tests |
|---|---|---|---|---|
| Authentication | `app.enterprise_auth`, OIDC/JWT | Implemented | Typed principal; prod dev-token rejected | `test_enterprise_auth`, `test_auth_context`, JWT/OIDC suites ✅ |
| Authorization | `require_*` guards, role/tenant | Implemented | Fail-closed | `test_permission_authorization`, `test_high_risk_route_permission_guards` ✅ |
| Authenticated Principal | `app.security.principal` | Implemented | Header cannot grant tenant authority | `test_directive_002_tenant_context` ✅ |
| Tenant Context / Isolation | `TenantMembership`, tenant_context | Implemented | Cross-tenant blocked | `test_tenant_isolation`, `test_cross_hospital_tenant_isolation_security` ✅ |
| Role Enforcement | `require_roles/tenant_roles` | Implemented | — | `test_inspection_role_permissions` ✅ |
| Secrets Management | env + hashing (token_urlsafe/SHA-256) | Implemented | Keys hashed, never retrievable | foundation secrets audit |
| Audit | `enterprise_audit_service` (hash chain) | Implemented | Append-only, tamper-evident | `test_audit_chain_verification`, `test_audit_immutability` ✅ |

## Clinical inspection intelligence

| Component | Source | Class | Notes |
|---|---|---|---|
| Inspection Engine | inspection workflow services/routes | Implemented | State machine; closure tested (`test_core_inspection_workflow_closure` ✅) |
| Image Service | image ingestion/`RetainedImage` | Implemented | Owner of image bytes; sha256 |
| Image Quality | `ImageQualityAssessment`, quality svc | Implemented | Quality ≠ cleanliness |
| Vision Engine | ML inference adapter, candidate path | Partially Implemented | Engineering path; no governed/certified model |
| Instrument/Tray Intelligence | instrument registry/services | Implemented | Identity via LCID |
| Anatomy/Zone Mapping | anatomy/zone services | Implemented | Engineering zones (not patient anatomy) |
| Observation/Risk Engine | decision engine, risk services | Implemented | Human-review-gated; fail-closed |
| Baseline Engine | baseline library/comparison | Implemented | `test_baseline_image_library` ✅ |
| Digital Twin Engine | `digital_twin_id` identity + services | Partially Implemented | Identity anchor; aggregate record = Future |
| Evidence Engine | compliance evidence bundle svcs | Implemented | `test_evidence_authorization_baseline` ✅ |
| Reporting Engine | evidence release/reporting svcs | Implemented | Governed report artifacts |

## Governed knowledge

| Component | Source | Class | Tests |
|---|---|---|---|
| Annotation | `annotation_database` model + svcs | Implemented | `test_annotation_database` ✅ |
| Ground Truth | `Annotation` GT (ACTIVE) | Implemented | (covered above) |
| Baseline Governance | `baseline_image_library` + lifecycle | Implemented | ✅ |
| Dataset Registry | `dataset_governance` + `dataset_registry` | Implemented | `test_dataset_registry` ✅ |
| Dataset Eligibility | `dataset_eligibility_service` | Implemented | `test_dataset_eligibility` ✅ |
| Dataset Lineage | registry linking columns | Implemented | (schema-validated) |
| Candidate Model Registry | `model_registry` | Implemented | `test_candidate_model_training` ✅ |
| Model Promotion | `candidate_promotion`, `model_promotion` | Implemented | ✅ |
| Experiment Tracking | training run id + config | Partially Implemented | First-class experiment record = Planned |
| Knowledge Graph | knowledge/registry services | Implemented | — |

## Supporting services

Workflow (`workflow_forge`), Analytics, Marketplace, Subscription/SLA, Vendor
Scorecard, Tenant Bootstrap, PDF Generation, Notification, Integration Adapters —
all **Implemented** as governed, tenant-scoped services; several are enterprise/
commercial surface area outside the core inspection pipeline (READY w/ conditions).

## AI governance

| Component | Source | Class | Notes |
|---|---|---|---|
| Candidate Models | `model_registry` + promotion | Partially Implemented | No governed/certified model exists |
| Placeholder Logic | safe unavailable-model states | Implemented | Isolated; never emits confident result |
| Specialist / Council components | specialist services, council_leadership | Implemented | Decision-support-only; human-authoritative |
| Human Review | review/adjudication/supervisor | Implemented | Authoritative; fail-closed |
| Confidence / Unknown-state | result contract | Implemented | Reviewer vs. AI confidence separated; Unknown valid |
| Safety Escalation | contamination-safety invariant | Implemented | Fail-closed to human/supervisor |

## Known cross-cutting gaps (see risk register)

Governance-in-code enforcement (Directives 006–009 migration steps), physical lab /
governed dataset / certified model (execution prerequisites), deprecated
`app.audit.log_audit_event` shim still called by some routes, Directive 005 doc
consolidation, and observed CI non-execution on PRs despite configured workflows.
