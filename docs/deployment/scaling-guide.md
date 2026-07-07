# Scaling Guide

## Scaling dimensions

LumenAI scales along three largely independent dimensions:

1. **Inspection volume** — how many inspections/month a tenant (or the
   whole shared deployment) processes.
2. **Tenant count** — how many distinct facilities/customers share one
   deployment (see `docs/deployment/multi-tenant-deployment-guide.md`).
3. **Concurrent users** — how many SPD staff are actively using the
   system at once (capture, review queues, dashboards).

## Application tier

Stateless FastAPI replicas scale horizontally — add replicas behind the
load balancer as request volume grows (see
`docs/deployment/high-availability-guide.md` for the same architecture
serving redundancy, not just capacity). There is no code-level ceiling on
replica count; the practical limit is database connection capacity.

## Database tier

The database is the eventual bottleneck at scale. Growth levers, in
order of typical cost/complexity:

1. **Connection pooling** (PgBouncer or managed equivalent) — the first
   and cheapest lever before vertical scaling.
2. **Vertical scaling** (more CPU/RAM on the primary) — straightforward
   with managed Postgres providers, no application change required.
3. **Read replicas** — dashboard/analytics queries (Phase 15/18/20/21/23
   aggregation endpoints) are read-heavy and safe to route to a replica;
   write paths (inspection creation, supervisor review, ledger entries)
   must stay on the primary.
4. **Indexing review** — every tenant-scoped table already indexes
   `tenant_id`; high-volume tenants should be monitored for query plans
   on frequently-filtered columns (`created_at`, `instrument_type`,
   `inspection_id`) as volume grows.

## Background job scaling

Scheduled jobs (Phase 15 prediction scheduler, RWE scheduler, quality
intelligence, global aggregation) run on a single leader today (see
`docs/deployment/cloud-architecture-guide.md`). At very high tenant
counts, these may need to shard by tenant across multiple workers —
tracked as a future scaling enhancement, not yet required at current
deployment scale.

## Aggregation query cost

The heavier dashboard aggregations (Phase 20 command center's
`facility_readiness`, Phase 21's `enterprise_knowledge_analytics`, Phase
23's CIOS dashboard) currently query up to 5,000 recent inspections per
call and compute in Python rather than in SQL. This is intentional at
current scale (keeps the aggregation logic readable and testable in one
place) but is the first place to invest in either:

- Moving the aggregation into SQL (`GROUP BY`/window functions), or
- Caching the result with a short TTL,

once a single tenant's inspection volume or the shared deployment's
combined dashboard-query rate makes the current approach measurably slow.
This is flagged here as a known scaling ceiling, not hidden as if it
scales infinitely.

## Capacity planning checklist

- [ ] Estimate the customer's expected inspections/month (see the ROI
  model's per-segment benchmarks in `docs/commercial/roi-model.md` for
  typical community/regional/academic hospital volumes)
- [ ] Size the database connection pool for expected concurrent replicas
  × expected concurrent requests per replica
- [ ] Confirm backup storage capacity accounts for retained training
  images if the tenant opts into image retention
- [ ] Load-test the dashboard aggregation endpoints at the customer's
  expected inspection volume before go-live for a large deployment
