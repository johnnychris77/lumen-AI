# LPR-DIR-027 — Blocker Classification (Workstream 2)

Every remaining blocker on IRC-1 (`5c22345`), classified **Pilot Blocking** /
**Production Blocking** / **Non-blocking**. Source: LPR-DIR-026 BASELINE_SECURITY_VERIFICATION.md
+ the merged release-blocker register (`docs/version-1.1/RELEASE_BLOCKER_REGISTER.md`).

## Legend
- **Pilot Blocking** — must be satisfied before *any* controlled pilot can start.
- **Production Blocking** — must be satisfied before production, not strictly before a
  supervised pilot on a managed environment, but still open.
- **Non-blocking** — tracked, not gating.

## Classification

| ID | Sev | Item | Status on IRC-1 | Classification | Rationale |
|---|---|---|---|---|---|
| SEC-C-01 | CRITICAL | Webhook fail-open + tenant injection | **CLOSED (code)** | — (resolved) | Fix merged + code-verified fail-closed |
| SEC-H-01 | HIGH | Hardcoded secret fallbacks | OPEN (partial) | **Production Blocking** | Prod startup guard mitigates; full removal before production |
| SEC-H-02 | HIGH | No fail-closed startup secret validation | OPEN (partial) | **Production Blocking** | Startup guards + per-request webhook enforcement exist; `Settings.validate()` gap remains |
| PERF-07 | HIGH | No production/representative load test | OPEN (infra) | **Production Blocking** | A supervised pilot is low-volume; full load test gates production |
| SCAL-01 | HIGH | Single Postgres SPOF + single worker | OPEN (infra) | **Pilot Blocking** | A pilot still needs a **managed environment** with backed-up Postgres; SPOF on real clinical data is unacceptable even at pilot scale |
| RES-01 | HIGH | In-process scheduler duplicates across replicas | OPEN (infra) | **Production Blocking** | Single-replica pilot avoids duplication; gates multi-replica production |
| OPS-INC-01 | HIGH | No incident response / on-call / alerting | OPEN (infra/process) | **Pilot Blocking** | A clinical pilot **requires** alerting + an on-call path for safety events |
| OPS-DEP-01 | HIGH | Production deploy is a stub (echoes kubectl) | OPEN (infra) | **Pilot Blocking** | No real deploy path → no managed environment to run a pilot on |
| OPS-DEP-02 | HIGH | No executed rollback drill | OPEN (infra) | **Pilot Blocking** | A clinical pilot **requires** a verified rollback before go-live |
| AR-16..18 | MAJOR | Audit atomicity, dataset-freeze, dedup TOCTOU | OPEN | **Non-blocking** | Targeted code items; not pilot-gating |
| DOC-01 | LOW | Stale docstring `integrations.py:796` | OPEN (cosmetic) | **Non-blocking** | Documentation nit; code is fail-closed |
| GATE-RW | GATE | No site/operators/equipment/managed env/real images | OPEN (real-world) | **Pilot Blocking** | The pilot's defining prerequisites (see Workstreams 3–4) |

## Summary

- **Pilot Blocking (OPEN): 5** — SCAL-01 (managed/backed-up DB), OPS-INC-01 (alerting/IR),
  OPS-DEP-01 (deploy path), OPS-DEP-02 (rollback drill), GATE-RW (site/operators/
  equipment/env/images).
- **Production Blocking (OPEN): 4** — SEC-H-01, SEC-H-02, PERF-07, RES-01.
- **Non-blocking: 3** — AR-16..18, DOC-01.
- **Resolved: 1** — SEC-C-01.

**Determination:** **5 Pilot-Blocking items remain OPEN.** None is closable from the
repository; all require a managed environment, real-world engagement, or executed
operational drills. The entry gate cannot pass while any Pilot-Blocking item is open.
