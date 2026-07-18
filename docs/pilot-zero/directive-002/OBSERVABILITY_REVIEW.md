# LPZ-DIR-002 — Observability Review (increment 2)

## Current state (inspected in `app/main.py`)

| Probe / signal | Endpoint | Behavior |
|---|---|---|
| Liveness | `GET /health` | 200 if the process is alive; returns version + environment. |
| Readiness | `GET /ready` | 200 only if the database is reachable (`SELECT 1`); 503 otherwise. |
| Metrics | `GET /metrics` | Prometheus text; gated by `METRICS_TOKEN` or localhost-only. |
| Request logging | middleware | request/response logging present; a deprecation shim routes legacy `app.audit.log_audit_event` to the hash-chained enterprise audit service. |

Liveness and readiness are already **differentiated** (a strength). Metrics are
access-controlled. Domain health services exist (`nexus_health`, `phoenix_platform_health`, storage `storage_health_check`).

## Gap addressed this increment (small, safe, tested)

`GET /ready` previously validated only the database and reported a flat
`{status, database}`. It now returns a per-dependency `checks` block:

```json
{
  "status": "ready",
  "database": "ok",
  "checks": { "database": "ok", "object_storage": "...", "configuration": "ok" }
}
```

Design rules (fail-safe, not fail-noisy):
* **Database remains the only hard readiness gate** — 503 iff the DB is
  unreachable. Behavior for existing orchestrators is unchanged.
* **Object storage** and **configuration** are *soft* sub-checks: reported for
  observability but they never independently flip readiness to 503, so a degraded
  soft dependency cannot black-hole traffic the app can still serve.
* The storage sub-check is wrapped so it can never raise out of the probe.

Covered by `tests/test_directive_002_endpoint_governance.py::TestHealthProbes`.

## Deferred (documented, not done — avoids risky churn on frozen architecture)

* **Startup probe** — a dedicated `/startupz` distinct from readiness (for slow
  first-boot migrations) is recommended but not added; readiness currently
  doubles as the startup signal.
* **Redis / queue health** — only wire these into `/ready` as *soft* checks once
  their client singletons are confirmed always-initialized in prod; adding them
  blindly risks false 503s. Tracked as a follow-up.
* **Structured (JSON) logging everywhere** — request logging exists; a uniform
  structured-logging pass (correlation-id propagation, replacing remaining silent
  `except Exception: pass` handlers) is a larger, cross-cutting change and is
  **out of scope** for this increment per the "smallest safe remediation" rule.
  A grep-based inventory of silent handlers is recommended as the first task of
  that follow-up.

## Disposition

Health/readiness/liveness/metrics are production-grade with the small readiness
enrichment added here. Structured-logging uniformity and additional soft
dependency checks are recommended follow-ups, not blockers.
