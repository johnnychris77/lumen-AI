# LPR-DIR-018 — Continuous Improvement Backlog (Phase 7)

A prioritized, evidence-based backlog seeded from the **real** findings across
Production Readiness Phases 1–6 (no launch data — no live feature/customer requests
exist yet). This is the single most useful, honest artifact this phase can produce:
the concrete work required to reach a production launch and to improve thereafter.

## P0 — Launch-blocking (must close before any production launch)

| ID | Item | Source | Owner |
|---|---|---|---|
| CI-P0-1 | Webhook fail-closed: require signing secret at startup; reject unsigned; bind tenant to verified signature not `X-Tenant-Id` | SEC-C-01 (CRITICAL) | Security Eng |
| CI-P0-2 | Remove HS256 secret fallbacks; invoke `config.validate()` at startup; refuse boot on missing secrets | SEC-H-01/02 | Backend Eng |
| CI-P0-3 | Run production load/stress/soak test on multi-worker + Postgres; define SLOs | PERF-07 | SRE |
| CI-P0-4 | Provision HA PostgreSQL (replicas/failover) + multi-worker (gunicorn+UvicornWorker) + tune pool (+PgBouncer) | SCAL-01 | Infra |
| CI-P0-5 | Scheduler leader-election / single scheduler pod | RES-01 | Backend Eng |
| CI-P0-6 | Stand up alerting (SLO→Alertmanager→on-call) + adopt IR/on-call/postmortem; run a game-day | OPS-INC-01 | SRE |
| CI-P0-7 | Wire real, verified production deploy + execute a rollback drill | OPS-DEP-01/02 | DevOps |

## P1 — High-value hardening (technical-debt backlog)

| ID | Item | Source |
|---|---|---|
| CI-P1-1 | Make audit write atomic with business write (transaction/outbox) | AR-16 |
| CI-P1-2 | Enforce `frozen` guard on dataset entry writes | AR-17 |
| CI-P1-3 | Unique `(tenant_id, image_sha256)` + integrity-error handling | AR-18 |
| CI-P1-4 | Observability depth: latency histograms + per-endpoint labels + pool/queue gauges + tracing | OPS-OBS-01/03 |
| CI-P1-5 | Unify CI + prod dependency manifests (pin CI) | DH-01/SEC-SC-01 |
| CI-P1-6 | Container non-root user | SEC-INF-01 |
| CI-P1-7 | Reconcile k8s/Helm to one authoritative IaC | ENV-01/HA-01 |
| CI-P1-8 | Access-review + maintenance-window + audit-review cadence + patch/hotfix runbook | OPS-GOV-03/05, CM-01/03 |

## P2 — Maintainability / performance improvements

| ID | Item | Source |
|---|---|---|
| CI-P2-1 | Decompose `enterprise_intake.py` god-module (10.5 kLOC, F/66) | SR-02 |
| CI-P2-2 | Consolidate duplicated helpers into `app/common/` | SR-01 |
| CI-P2-3 | Route config through central `Settings` (reduce sprawl) | CFG-01 |
| CI-P2-4 | Profile + fix N+1 queries (add `selectinload` on hot list/report endpoints) | DB-05 |
| CI-P2-5 | Offload heavy report/evidence generation to the RQ worker | SCAL-03 |
| CI-P2-6 | Trim startup import time (~24 s) via lazy router import | PERF-05 |
| CI-P2-7 | Retention/archival policy + audit partitioning | CAP-01 |

## P3 — Automation opportunities
CI gates for `ruff format`, `mypy`, `vulture`, import-cycle, coverage %, OpenAPI-diff,
container-image CVE scan, license scan, dependabot/SHA-pin Actions (Phase 2/3/5).

## Feature / customer requests
**None recorded** — no production customers exist. This section is intentionally
empty and will be populated post-launch from real customer feedback.

## Note
This backlog is the honest deliverable of Phase 7 given no launch has occurred: it
converts six phases of evidence into a sequenced execution plan. Nothing here is a
new feature or architectural change — it is stabilization + hardening.
