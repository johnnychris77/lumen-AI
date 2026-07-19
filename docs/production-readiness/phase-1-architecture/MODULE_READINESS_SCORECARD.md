# LPR-DIR-012 — Module Readiness Scorecard

Each subsystem is scored 0–5 across 14 dimensions and assigned one status:
READY / READY WITH CONDITIONS / NOT READY / PLACEHOLDER / DOCUMENTED ONLY /
DEPRECATED / OUT OF SCOPE. Scores are evidence-based; weak evidence is **not**
converted into an optimistic score.

**Dimensions:** Rc=Responsibility clarity, Bi=Boundary integrity, Dh=Dependency
health, Se=Security, Ti=Tenant isolation, Au=Auditability, Di=Data integrity,
Fh=Failure handling, Te=Testability, Ob=Observability, Do=Documentation, Ow=Ownership,
Ma=Maintainability, Sc=Scalability. (0–5 each.)

| Subsystem | Rc | Bi | Dh | Se | Ti | Au | Di | Fh | Te | Ob | Do | Ow | Ma | Sc | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Authentication | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 5 | 4 | 4 | **READY** |
| Authorization | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 5 | 4 | 4 | **READY** |
| Tenant isolation | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 5 | 4 | 4 | **READY** |
| Audit (hash chain) | 5 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 3 | 5 | 4 | 4 | **READY W/ CONDITIONS** (deprecated shim) |
| Database / persistence | 5 | 4 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 4 | 3 | 4 | 4 | 3 | READY W/ CONDITIONS |
| Object storage | 4 | 4 | 4 | 4 | 4 | 5 | 5 | 4 | 3 | 4 | 4 | 4 | 4 | 3 | READY W/ CONDITIONS |
| Inspection Engine | 5 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | **READY** |
| Image Service / Quality | 5 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | 4 | READY |
| Annotation / Ground Truth | 5 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 4 | 5 | 4 | 4 | 4 | **READY** |
| Baseline Engine / Governance | 5 | 4 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 4 | 5 | 4 | 4 | 4 | READY |
| Digital Twin Engine | 4 | 4 | 4 | 4 | 5 | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | 4 | READY W/ CONDITIONS (aggregate record) |
| Evidence Engine | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | **READY** |
| Reporting Engine | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | READY W/ CONDITIONS |
| Dataset Registry / Eligibility / Lineage | 5 | 4 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 4 | 5 | 4 | 4 | 4 | READY W/ CONDITIONS (immutability enforcement) |
| Candidate Model Registry / Promotion | 4 | 4 | 4 | 4 | 5 | 5 | 5 | 4 | 5 | 3 | 5 | 4 | 4 | 3 | READY W/ CONDITIONS (enforcement; no governed model) |
| Vision Engine (inference) | 3 | 4 | 4 | 4 | 4 | 4 | 4 | 5 | 4 | 3 | 4 | 4 | 3 | 3 | **NOT READY** (no governed/certified model) |
| Experiment Tracking | 3 | 3 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 4 | 3 | 3 | READY W/ CONDITIONS (first-class record) |
| Human Review / Safety Escalation | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | **READY** |
| Placeholder logic (unavailable-model) | 5 | 5 | 5 | 5 | 5 | 4 | 5 | 5 | 5 | 4 | 4 | 4 | 5 | 5 | **PLACEHOLDER (isolated, READY)** |
| Deployment / Infra | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 4 | 4 | 4 | 3 | READY W/ CONDITIONS (HA) |
| CI/CD | 3 | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 3 | READY W/ CONDITIONS (PR execution unconfirmed) |
| Supporting svcs (Workflow/Analytics/Marketplace/Subscription/SLA/Vendor/PDF/Notification/Integrations) | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 3 | READY W/ CONDITIONS |
| Physical lab acquisition | 0 | — | — | — | — | — | — | — | — | — | 5 | 4 | — | — | **DOCUMENTED ONLY / OUT OF SCOPE (execution)** |

## Readiness summary

* **READY (7):** Authentication, Authorization, Tenant isolation, Inspection
  Engine, Annotation/Ground Truth, Evidence Engine, Human Review — the
  safety-critical core, all test-verified.
* **READY WITH CONDITIONS (majority):** governance/data/model/infra/CI modules —
  conditions are enforcement-in-code, HA, CI execution, and doc/ADR completion.
* **NOT READY (1):** Vision Engine inference — no governed/certified model exists
  (correct for this stage; not a defect).
* **PLACEHOLDER (isolated, READY):** unavailable-model safe states.
* **DOCUMENTED ONLY / OUT OF SCOPE:** physical lab acquisition.

No module scored READY carries an unresolved **Critical** architectural finding.
