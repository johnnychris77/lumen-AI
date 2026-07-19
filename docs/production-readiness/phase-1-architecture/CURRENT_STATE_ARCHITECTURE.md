# LPR-DIR-012 — Current-State Architecture

**Basis:** implemented code at baseline `c9797b2` (not documentation alone).

## Repository structure (top level)

```
backend/        FastAPI + SQLAlchemy application (147 models, 489 services, 205 route modules)
frontend/       React + TypeScript + Vite SPA
alembic/, backend/alembic/  migrations (13 versions)
dataset/        governed dataset filesystem scaffold
docs/           architecture, ADRs, foundation, pilot-zero, pilot-alpha, production-readiness
docker/, docker-compose*.yml, Dockerfile, helm/, k8s/, render.yaml   deployment topology
observability/, ops/   monitoring/operations assets
scripts/, validation/  tooling incl. endpoint-inventory generator
.github/workflows/     11 CI workflow definitions
```

## Runtime components

* **Frontend SPA** (React/TS/Vite) — user interface; talks to the backend HTTP API.
* **Backend API (`app.main:app`)** — FastAPI application; the single application
  runtime. Groups logical "engines" (inspection, Digital Twin, baseline, evidence,
  annotation, vision, audit, reporting) as service + route modules.
* **Database** — SQLAlchemy ORM; PostgreSQL is the configurable authoritative DB
  (foundation), SQLite used for tests.
* **Object/file storage** — governed object storage service (foundation); image
  bytes owned by `RetainedImage`.
* **Audit subsystem** — hash-chained enterprise audit
  (`enterprise_audit_service`), tamper-evident.

**Deployment model:** a **modular monolith** (single FastAPI runtime, one database)
with containerized deployment (Docker/Compose/Helm/K8s manifests present).

## Control flow (request)

```
User → Frontend SPA → HTTP API (API Gateway = FastAPI routing + auth deps)
     → Authenticated Principal resolution (typed) → Tenant Context (TenantMembership)
     → Authorization guards (require_* / role / tenant) → Service layer
     → Database / Object storage → Audit event (hash-chained) → Response
```

## Data flow (governed inspection pipeline)

```
Instrument identity (LCID) → Inspection → Image (RetainedImage, sha256) → Metadata
→ Annotation (AnnotationVersion) → Ground Truth (ACTIVE) → Baseline (approved)
→ Digital Twin (identity anchor) → Dataset (DatasetVersion) → Candidate Model (registry)
→ Human Review → Evidence Package → Audit → Report
```

## Trust boundaries (summary; detail in `TRUST_BOUNDARY_ARCHITECTURE.md`)

User→Frontend, Frontend→API, API→Principal, Principal→Tenant, Tenant→Authorization,
Service→DB, Service→Storage, Model→Governed workflow, Reviewer→Disposition,
System→Audit chain, Evidence→Immutable archive, External integration→Platform.

## Persistence boundaries

* Authoritative DB owns governed records (users, tenants, inspections, annotations,
  GT, baselines, datasets, models, audit).
* `RetainedImage` is the sole owner of image bytes; other modules reference by id +
  `image_sha256` (no duplicate byte stores).
* Append-only history for GT / baselines / datasets / audit.

## External interfaces

HTTP API (1,912 endpoints), signed webhooks (billing, integrations), OIDC/JWT auth
inputs, object storage, and report/evidence export artifacts.

## Synchronous vs. asynchronous

* **Synchronous:** the request→response inspection/annotation/evidence path.
* **Asynchronous / scheduled:** ML eval nightly (CI), background/monitoring and
  drift services (Shadow/Advisor lineage), notification paths.

## Startup path

`app.main` constructs the FastAPI app, wires routers, initializes DB/session and
auth dependencies; `conftest.py` force-imports models for test parity. Readiness is
gated by `/ready` with per-dependency checks (DB hard-gate).

## Shutdown path

Standard ASGI lifespan teardown; DB sessions closed per request; no long-lived
in-process state that requires special drain beyond in-flight request completion.

## Deployment topology

Containerized single-runtime backend + SPA, with Docker Compose (dev/prod),
Helm/K8s manifests, `render.yaml`, and `observability/` assets. PostgreSQL as
authoritative DB; object storage for artifacts; 11 CI workflows defined.

## Implemented vs. planned

* **Implemented:** the governed inspection→evidence→audit pipeline, auth/tenant/
  authorization, annotation/GT/baseline/dataset/model registries, hash-chained
  audit, evidence packages — all exercised by the 186/186 validation subset.
* **Planned / documented-only:** physical lab acquisition (no governed images yet),
  governed/certified candidate model, and several governance-in-code enforcement
  steps documented across Directives 006–009 (see `SYSTEM_INVENTORY.md` lifecycle
  states).
