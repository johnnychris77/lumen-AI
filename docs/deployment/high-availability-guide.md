# High Availability Guide

## Design goal

No single component failure should take the whole platform down for a
customer relying on LumenAI as their pre-sterilization quality gate.

## Application tier

- Run the FastAPI backend as multiple stateless replicas behind a load
  balancer. The application holds no in-process session state that would
  break under horizontal scaling — auth is stateless JWT/OIDC
  (`docs/security/production-oidc-deployment-guide.md`), and every
  request re-establishes its own DB session (`app/deps.py::get_db`).
- Health checks: `GET /api/agents/health` (Phase 22 agent registry
  rollup) and `GET /api/cios/dashboard`'s `system_health` field
  (Phase 23) both report a real, computed health status suitable for a
  load balancer health-check probe — neither is a fabricated "always
  ok" endpoint.
- The frontend is a static build (`npm --prefix frontend run build`) —
  serve it from a CDN with multi-region edge caching; it has no
  single-instance availability concern.

## Data tier

- PostgreSQL with a hot standby / read replica for failover (managed
  Postgres offerings on Render/Railway/Fly provide this — see the
  respective deployment docs). A failover to a standby should be
  automated by the managed database provider, not a manual DBA action,
  wherever the hosting platform supports it.
- Connection pooling (e.g. PgBouncer or the provider's built-in pooler)
  to avoid exhausting connections across multiple application replicas.

## Background jobs

- Scheduled jobs (prediction scheduler, RWE scheduler, integration
  scheduler, quality-intelligence scheduler, global-aggregation
  scheduler — registered in `app/main.py` via APScheduler) should run on
  a single designated worker/leader to avoid duplicate execution, with a
  standby worker ready to take over the schedule if the leader fails.

## What "available" does NOT mean here

Availability of the *platform* is separate from clinical safety
guarantees. Even at 100% platform uptime, every recommendation still
requires human supervisor validation (Design Principle 4,
`docs/architecture/design-principles.md`) — high availability makes the
tool reliably accessible, it does not reduce or replace the human review
step.

## Degraded-mode behavior

If a downstream dependency degrades (e.g. the knowledge graph's
enterprise analytics query is slow under load), the platform should
degrade gracefully rather than fail the whole request:

- Dashboard aggregation functions (Phase 20/21/23) already return `None`
  for a metric they can't compute rather than raising — the same
  principle should extend to infrastructure-level degradation (timeouts
  return partial dashboards, not 500s, wherever safely possible).
- Core inspection creation and scoring (`POST /api/inspections`) is the
  highest-priority path to keep available even if analytics/dashboard
  endpoints are temporarily degraded.

## Multi-region considerations

See `docs/deployment/cloud-architecture-guide.md` for whether a given
deployment needs multi-region active-active, or single-region with a
cold/warm disaster-recovery region (see
`docs/deployment/disaster-recovery-guide.md`) — most single-hospital and
regional health-system deployments do not need active-active multi-region;
it becomes a relevant conversation at the scale of a national health
system or a multi-tenant hosted offering serving many customers.
