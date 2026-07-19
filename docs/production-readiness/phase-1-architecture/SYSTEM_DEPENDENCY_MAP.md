# LPR-DIR-012 — System Dependency Map

**Basis:** implemented code at `c9797b2`.

## Layered dependency direction (intended)

```
Frontend SPA
   ↓ (HTTP only)
Routes (transport)
   ↓
Services (business logic)
   ↓
Models / DB (SQLAlchemy)   +   Object storage   +   Audit chain
```

Cross-cutting dependencies (called by services, not the reverse): **auth /
principal**, **tenant context**, **audit**, **evidence**, **LCID identity**.

## Domain dependency chains (governed pipeline)

```
LCID identity ──▶ Inspection ──▶ RetainedImage(sha256) ──▶ Annotation ──▶ Ground Truth
Ground Truth ──▶ Baseline ──▶ Digital Twin(identity) ──▶ Dataset(version) ──▶ Model registry
Every stage ──▶ Audit chain (enterprise_audit_service)
Every write  ──▶ Authenticated principal + Tenant context
```

## Dependency classes

| Class | Examples |
|---|---|
| Module→module | routes→services→models; services→auth/tenant/audit |
| Service→service | dataset_builder→dataset_split→dataset_integrity; baseline_comparison→image_similarity |
| Database | all services→SQLAlchemy session; PostgreSQL authoritative (SQLite for tests) |
| Configuration | env/settings→startup; `/ready` hard-gates DB |
| Authentication | protected routes→`enterprise_auth`/principal |
| Tenant context | write paths→`TenantMembership` |
| Audit | governed writes→`enterprise_audit_service` (+ deprecated `app.audit` shim) |
| Evidence | evidence engine→images/annotations/GT/baseline/audit |
| Digital Twin / Baseline / Annotation / GT / Dataset / Model | as chained above |
| Third-party packages | FastAPI, SQLAlchemy, pydantic, passlib, alembic, cyclonedx (SBOM), CV/ML libs |
| External services | OIDC/JWT IdP, object storage, billing (Stripe webhooks), integration webhooks |
| Deployment | Docker/Compose/Helm/K8s/render; 11 CI workflows |

## Dependency findings

* **Circular dependencies:** none surfaced in the validated pipeline; import-cycle
  detection is recommended as a standing CI check (not currently proven in CI — see
  DEPENDENCY_RISK_REGISTER D-04).
* **Reverse dependencies:** models must not import services/routes — spot-checked
  clean; enforce with a lint/architecture check in a later phase.
* **Hidden dependencies:** the deprecated `app.audit` shim hides a second path to
  the audit chain (B-01).
* **Optional-treated-as-mandatory:** the candidate model is optional (safe
  unavailable-model states) and correctly treated as optional.
* **Mandatory-treated-as-optional:** none found for auth/tenant/audit — these are
  mandatory and enforced.
* **Single points of failure:** the single database and single backend runtime
  (modular monolith) — mitigated by `/ready` gating, backup/restore + DR (measured
  RTO/RPO), and horizontal container scaling; tracked as recovery/scalability risk.
* **Duplicate libraries / unclear ownership:** none confirmed; SBOM (100
  components) provides the dependency baseline.
* **Transitive security exposure:** managed via SBOM + `security-baseline` /
  `security-hardening-validation` CI workflows (configured; execution to be
  confirmed — see risk register).

See `DEPENDENCY_RISK_REGISTER.md` for scored risks.
