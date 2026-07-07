# Cloud Architecture Guide

## Supported deployment targets

LumenAI is cloud-agnostic by design (FastAPI + PostgreSQL + a static
frontend build) and has documented deployment paths for:

- **Render** — `docs/deployment/RENDER_DEPLOYMENT.md`,
  `RENDER_DEPLOYMENT_READINESS.md`
- **Railway** — `docs/deployment/RAILWAY_DEPLOYMENT.md`
- **Fly.io** — `docs/deployment/FLY_DEPLOYMENT.md`
- **Generic cloud/Kubernetes** — `docs/deployment/CLOUD_DEPLOYMENT_PLAN.md`,
  and this guide

Pick the managed-platform path (Render/Railway/Fly) for fastest
time-to-production; pick the generic cloud path for a customer that
requires deployment into their own cloud account/VPC for compliance
reasons.

## Reference architecture

```
                     ┌─────────────────┐
                     │   CDN / Static   │
                     │  Frontend Host   │  (Vite build output)
                     └────────┬─────────┘
                              │
                     ┌────────▼─────────┐
                     │  Load Balancer /  │
                     │  Reverse Proxy    │  (TLS termination)
                     └────────┬─────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
        │  FastAPI   │   │  FastAPI   │   │  FastAPI   │   (stateless replicas —
        │  Backend   │   │  Backend   │   │  Backend   │    see high-availability-guide.md)
        └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   PostgreSQL       │  (primary + standby —
                    │   (primary)        │   see high-availability-guide.md)
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Backup storage /  │  (see backup-restore-guide.md)
                    │  cross-region copy │
                    └───────────────────┘

        ┌───────────────────────────────────┐
        │  Background schedulers (single     │
        │  leader): prediction, RWE,         │
        │  integration, quality-intelligence, │
        │  global-aggregation (app/main.py)  │
        └───────────────────────────────────┘
```

## Network boundaries

- The frontend never talks to the database directly — all data access
  goes through the FastAPI backend's authenticated, RBAC-gated routes.
- Outbound integrations (external system connectors,
  `app/models/external_connector.py`) are opt-in per tenant and gated by
  a signed BAA where PHI-adjacent data could be involved (see the
  integrations route's BAA check, exercised by
  `_seed_hipaa_baa` in the test suite).
- No component other than the backend holds a database credential.

## Statelessness and horizontal scaling

Every backend replica is interchangeable — there is no sticky-session
requirement and no in-memory state that would break if a request landed
on a different replica than a prior request from the same user. This is
what makes the horizontal-scaling story in
`docs/deployment/scaling-guide.md` straightforward: add replicas behind
the load balancer, no application-level coordination required beyond the
shared database.

## Environments

Maintain at least three environments per deployment:

1. **Production** — `APP_ENV=production`, real auth only, real data.
2. **Staging** — mirrors production configuration, used for pre-release
   verification (`docs/security/staging-security-smoke-test-checklist.md`).
3. **Development** — dev-auth tokens enabled, synthetic/demo data only
   (see `docs/deployment/GITHUB_PAGES_DEMO.md` for the public demo
   environment specifically, which is intentionally isolated from any
   real customer data).
