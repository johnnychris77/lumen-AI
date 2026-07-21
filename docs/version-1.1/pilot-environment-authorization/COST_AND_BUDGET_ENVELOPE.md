# COST & BUDGET ENVELOPE — LPR-DIR-031A

Cost-driver framework for the pilot-grade managed environment. **All figures below are
illustrative placeholders requiring Finance + the cloud owner to confirm against actual
provider pricing and the organization's contracts.** No figure here is an authoritative quote.

## 1. Cost drivers (what generates spend)
| Driver | Component | Notes |
|---|---|---|
| Compute | Managed Kubernetes control plane + ≥2 worker nodes | pilot-grade minimal nodes |
| Database | Managed PostgreSQL (smallest tier) + automated backup/PITR storage | backup retention adds storage cost |
| Storage | Persistent volumes + object store (images + backups) | grows with retention window |
| Networking | Ingress/load balancer + egress | LB is a common fixed monthly cost |
| TLS | Managed certificate | often free (ACME) or low cost |
| Observability | Metrics + logs retention (≥14d) + alerting | retention length is the main lever |
| Registry | Container image storage | small |

## 2. Illustrative monthly envelope (PLACEHOLDER — confirm with Finance)
| Tier | Illustrative range/mo | Intended use |
|---|---|---|
| Minimal (spin-up on demand, tear down between drills) | **$ TBD (low)** | run DIR-032 drills, then de-provision |
| Steady pilot-grade (kept running for the pilot window) | **$ TBD (moderate)** | continuous availability during the pilot |

> These placeholders are deliberately unfilled. Populate them from a real provider estimate
> before authorization; do not treat them as approved amounts.

## 3. Cost-control recommendations
- **Ephemeral-by-default:** provision for a drill window, capture evidence, de-provision — the
  IaC (spec C8) makes re-creation cheap and repeatable.
- Smallest tiers that still exercise ≥2 replicas (needed for RES-01 leader-election evidence).
- Short observability retention (≥14d) for the pilot window.
- Set a **billing alert / budget cap** on the pilot account before provisioning.

## 4. Approvals required for spend
Budget authorization is a **Finance + executive** decision recorded in
`AUTHORIZATION_DECISION_RECORD.md` (budget line). This document does **not** authorize spend;
it scopes what spend would cover.

## 5. Honesty note
No dollar amount here is validated. The executing context (this program) cannot price cloud
resources authoritatively and must not present placeholder ranges as approved budget.
