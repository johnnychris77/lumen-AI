# Commercial Packaging

## Relationship to the existing tier model

`docs/commercial/product-packaging.md` defines the current live
commercial tiers (Starter / Professional / and higher tiers) with
detailed feature/limit tables and is the authoritative source for
exact current limits and pricing linkage
(`docs/commercial/pricing-strategy.md`). This document defines the
**four-edition structure** Phase 24 asks for, mapping onto and extending
that existing model — it does not replace `product-packaging.md`'s detail,
it reframes the top-level edition names for enterprise/partner-facing
conversations.

## The four editions

### Community Edition
**Maps to:** the existing Starter tier (`docs/commercial/product-packaging.md`)
**For:** single-facility community hospitals, pilot programs, and
evaluation deployments.

| Dimension | Limit |
|---|---|
| Facilities | 1 |
| Users | Up to 10 |
| Inspection volume | Up to 2,000/month |
| AI findings | Blood, tissue, residue detection |
| Multi-agent pipeline (Phase 22) | Included |
| Knowledge graph explorer (Phase 21) | Included |
| Enterprise dashboards | Not included |
| Support | Email, 5-business-day SLA |

### Professional Edition
**Maps to:** the existing Professional tier
**For:** mid-size hospitals, multi-OR facilities, regional medical centers.

Adds to Community: predictive analytics, vendor intelligence, benchmarking
against network aggregates (Phase 15), pre-sterilization command center
(Phase 20), pilot validation dashboard (Phase 18). Support: priority email
+ business-hours chat, 2-business-day SLA.

### Enterprise Edition
**For:** health systems with multiple facilities, requiring multi-tenant
deployment, custom RBAC, and executive-level reporting.

Adds to Professional: multi-facility/multi-tenant deployment
(`docs/deployment/multi-tenant-deployment-guide.md`), the CIOS Enterprise
Health Dashboard (`/cios-dashboard`, Phase 23), the Clinical Decision
Ledger and full governance version tracking, custom SLA and dedicated
implementation support, SSO/OIDC. High-availability deployment option
(`docs/deployment/high-availability-guide.md`).

### Manufacturer Edition
**For:** instrument manufacturers and SPD vendors who want visibility into
their own instruments' real-world performance across LumenAI's network,
without access to any individual hospital's clinical data.

- Read access to anonymized, aggregated network benchmarks for their own
  instrument categories/models (Phase 15 network intelligence,
  anonymized per the CLAUDE.md cross-hospital intelligence constraint —
  never a specific hospital's raw data)
- Baseline submission and approval workflow
  (`app/models/baseline_library.py`, vendor baseline audit trail)
  for their own products
- Failure-mode and instrument-knowledge contribution
  (`app/models/instrument_knowledge.py`) — a manufacturer can contribute
  known failure modes and IFU references for their own instruments
- No access to any hospital's tenant-scoped inspection or supervisor
  review data, ever — this edition is architecturally read-scoped to
  anonymized cross-tenant aggregates only

## What every edition shares (non-negotiable, not a paid feature)

- Human-in-the-loop supervisor validation (Design Principle 4) —
  never gated behind a tier
- Tenant isolation and audit logging — always on
- The clinical ontology and knowledge graph reasoning — the core
  reasoning engine is the same across every edition; editions differ in
  scale, dashboards, and support, not in clinical reasoning quality

## Choosing an edition

See `docs/enterprise/enterprise-readiness.md`'s readiness gate for how to
confirm a given edition is appropriate for a prospective customer's scale
before selling it.
