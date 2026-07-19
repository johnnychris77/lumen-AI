# LPR-DIR-012 — Module Boundary & Responsibility Review

Each finding: ID, Severity (CRITICAL/MAJOR/MINOR/OBSERVATION), Component, Evidence,
Architectural/Security/Data impact, Recommended action, and whether architecture
change approval (Class B/C) is required.

## Clean boundaries (verified)

* **Auth → Tenant → Authorization → Service** is enforced *before* the service
  layer; header cannot grant tenant authority (Directive 002; tests pass).
* **`RetainedImage` sole owner of image bytes**; other modules reference by id +
  `image_sha256` — no duplicate byte stores.
* **Audit is a single hash-chained writer** (`enterprise_audit_service`);
  append-only, tamper-evident (tests pass).
* **Append-only history** for Ground Truth / baselines / datasets / audit.
* **AI is decision-support-only**; human review is authoritative and fail-closed.

## Findings

| ID | Sev | Component | Evidence | Impact | Recommended action | Approval |
|---|---|---|---|---|---|---|
| B-01 | MAJOR | Audit writer shim | `app.audit.log_audit_event` deprecated, still called (e.g. `routes/model_pipeline.py`, `routes/dataset_registry.py`) — observed as DeprecationWarning in the validation run | Maintainability; two call paths to the audit chain | Migrate callers to `enterprise_audit_service.record_enterprise_audit_event`; remove shim when call-count = 0 | Class A (cleanup) |
| B-02 | MAJOR | Governance gates in code | Directives 006–009 document GT-gating / separation-of-duties / dataset immutability / first-class experiment; not all enforced in code | Governance enforced by policy + tests, not universally by code | Implement enforcement (Directives 006–009 migration) | Class B |
| B-03 | MAJOR | Backend god-runtime | 489 services / 205 route modules in one runtime; many domains under one owner | Maintainability, knowledge concentration | Domain-scoped maintainership + package boundaries; no split for its own sake | Class B (ownership/boundary) |
| B-04 | MINOR | Persistence in routes | Some route handlers perform data logic directly (e.g. audit calls in `routes/*`) | Cohesion; transport layer holds business logic | Move persistence/audit into service layer incrementally | Class A |
| B-05 | MINOR | Digital Twin aggregate | Twin is an identity string, not an aggregate record | Ambiguous single-record ownership of twin lifecycle | Add governed aggregate twin (Directive 007 migration) | Class B (Future) |
| B-06 | OBSERVATION | Duplicate billing webhook path | Two handlers map `POST /api/billing/webhook` (`billing.stripe_webhook`, `billing_webhooks.billing_webhook`) per route inventory | Endpoint duplication; ambiguous owner | Confirm intended handler; deprecate the other | Class A |
| B-07 | OBSERVATION | Compatibility shims | Header-fallback/auth-consolidation follow-ups (Directive 002 F1/F5) remain | Compatibility code trending permanent | Complete migration in a later phase | Class B |

## Boundary categories

* **Clean boundaries:** auth/tenant/authorization chain; image ownership; audit
  writer; append-only history.
* **Weak boundaries:** route-layer persistence/audit calls (B-04); god-runtime
  ownership (B-03).
* **Boundary violations:** none CRITICAL found — no cross-tenant access, audit
  bypass, evidence mutation, or unsafe AI finalization surfaced in code or tests.
* **Duplicate capabilities:** billing webhook (B-06); deprecated audit shim (B-01).
* **Orphan capabilities:** none confirmed (route inventory shows 0 UNKNOWN
  classification).
* **God modules:** the backend runtime at the macro level (B-03).
* **Utility-with-authority:** the deprecated `app.audit` shim retains audit
  authority it should delegate (B-01).
* **Permanent compatibility shims:** B-07.

## Net assessment

**No CRITICAL boundary finding.** The safety-critical boundaries (tenant, auth,
audit, evidence, human authority) are clean and test-verified. The MAJOR findings
are maintainability/enforcement items suitable for later Production Readiness
phases under change control.
