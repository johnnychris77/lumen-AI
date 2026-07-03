# Deployment Framework

Overview of `docs/deployment/` — the Enterprise Deployment Kit — and how
its pieces fit together for an implementation team planning a rollout.

## The kit

| Guide | Answers |
|---|---|
| `enterprise-installation-guide.md` | How do we install this for an enterprise customer, start to finish? |
| `production-deployment-guide.md` | What does the production deployment actually look like mechanically? |
| `cloud-architecture-guide.md` | What's the reference architecture, and which cloud targets are supported? |
| `multi-tenant-deployment-guide.md` | Single-tenant or shared multi-tenant — how is isolation guaranteed? |
| `high-availability-guide.md` | How do we avoid a single point of failure? |
| `scaling-guide.md` | How does this grow with inspection volume, tenant count, and concurrent users? |
| `backup-restore-guide.md` | What's backed up, how often, and how do we restore it? |
| `disaster-recovery-guide.md` | What do we do if something goes badly wrong? |

Plus the platform-specific quick-start guides (`RENDER_DEPLOYMENT.md`,
`RAILWAY_DEPLOYMENT.md`, `FLY_DEPLOYMENT.md`) for managed-cloud
deployments, and `go-live-runbook.md` /
`PUBLIC_DEMO_READINESS_CHECKLIST.md` for pre-launch verification.

## Choosing a deployment path

```
Is this a managed-cloud (Render/Railway/Fly) deployment,
or does the customer require their own cloud account/VPC?
        │
        ├── Managed cloud → follow the platform-specific quick start,
        │                    then enterprise-installation-guide.md for
        │                    the enterprise-specific configuration steps
        │
        └── Customer-managed cloud → cloud-architecture-guide.md's
                                      reference architecture, deployed
                                      via the customer's own IaC
```

## Sequencing for a new enterprise deployment

1. Confirm the edition (`docs/enterprise/commercial-packaging.md`) — this
   determines whether multi-tenant, HA, or a custom SLA is in scope.
2. Provision per `enterprise-installation-guide.md`.
3. Configure tenancy per `multi-tenant-deployment-guide.md` if this is a
   shared or multi-facility deployment.
4. Configure HA per `high-availability-guide.md` if the edition/SLA
   requires it.
5. Verify backup/restore is working (`backup-restore-guide.md`) — before
   go-live, not after the first incident.
6. Run the post-install verification checklist
   (`enterprise-installation-guide.md`).
7. Hand off to the Customer Success team for onboarding
   (`docs/enterprise/customer-success-framework.md`).

## Ownership

Deployment engineering owns the guides in `docs/deployment/`; Customer
Success owns the handoff into `docs/customer/`. This document is the
seam between the two.
