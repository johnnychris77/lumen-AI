# LPA-DIR-011 — Component Interoperability Validation

**Purpose:** validate the interfaces between the platform's engine components in
integration. LumenAI's "engines" are logical groupings of the backend's 489
services + routes; interoperability is exercised by the integration test subset
(130/130 passed) and the endpoint-inventory governance (Directive 002).

## Interface validation

| Component (logical engine) | Backing modules | Interfaces validated with | Status |
|---|---|---|---|
| **API Gateway** | FastAPI `app.main`, routes, auth deps | Typed principal, fail-closed authz, endpoint inventory | ✅ Pass |
| **Inspection Engine** | inspection workflow services/routes | Session lifecycle + state machine (`test_core_inspection_workflow_closure`) | ✅ Pass |
| **Digital Twin Engine** | LCID identity, twin services | Twin resolution + linkage from inspection/dataset | ✅ Pass |
| **Baseline Engine** | baseline library/comparison/compatibility services | Approved-baseline retrieval + comparison contract | ✅ Pass |
| **Evidence Engine** | compliance evidence bundle services | Bundle assembly + checksum + authorization (`test_evidence_authorization_baseline`) | ✅ Pass |
| **Annotation Engine** | annotation DB + review services | Create/version/review interoperate with GT | ✅ Pass |
| **Knowledge Graph** | knowledge/registry services | Instrument/anatomy/registry references resolve | ✅ Pass |
| **Vision Engine** | ML inference adapter + candidate model path | Train→register→promote via API; safe unavailable-model states | ⚠️ Pass (engineering path; no governed model) |
| **Audit Engine** | enterprise audit (hash-chained) | Append-only chain + verification across modules | ✅ Pass |
| **Reporting Engine** | evidence release / reporting services | Report + evidence artifacts generated | ✅ Pass |

## Cross-cutting interoperability

* **Auth boundary consistent:** every engine's write endpoints resolve through the
  typed authenticated principal; unauthenticated writes are limited to the
  PUBLIC_BY_DESIGN set (Directive 002).
* **Audit is universal:** all engines emit hash-chained audit events, giving a
  single tamper-evident record across component boundaries.
* **Deprecation note:** `app.audit.log_audit_event` is deprecated and delegates to
  `enterprise_audit_service.record_enterprise_audit_event` (observed as a warning,
  not a failure) — a **minor** cleanup item (see gap analysis).

## Determination

**INTEROPERABILITY VALIDATED.** All ten logical engines interoperate across their
interfaces in integration, with a consistent auth boundary and a universal
tamper-evident audit chain. The Vision Engine's model path is validated at the
engineering level only (no governed/certified model).
