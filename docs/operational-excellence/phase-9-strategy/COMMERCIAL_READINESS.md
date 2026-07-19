# LPR-DIR-020 — Commercial Readiness (Phase 9)

## Framing

Commercial readiness assessed against real platform capabilities. Where a dimension
depends on live customers/revenue, it is marked **NOT AVAILABLE — not launched**, never
fabricated.

## Dimensions

| Dimension | State | Honest readiness |
|---|---|---|
| **Multi-tenancy** | `TenantMembership` authoritative (header cannot grant tenant authority); tenant-scoped data isolation enforced; 1,593 `require_*` guards | **Real and test-verified** — the strongest commercial foundation |
| **SaaS readiness** | Containerized (GHCR release), configurable Postgres + object storage, health/readiness probes, DR-drilled | **Partial** — gated by SCAL-01 (single-worker/SPOF), RES-01 (scheduler), OPS-DEP-01 (deploy stub), OPS-INC-01 (no IR/alerting) |
| **Licensing** | No entitlement/feature-flag licensing subsystem found | **Not built** (COM-01) |
| **Pricing models** | Prior pricing docs exist (commercial content); no billing enforcement wired beyond Stripe webhook (which carries SEC-C-01) | **Strategy only; NOT AVAILABLE as live pricing** (no customers) |
| **Onboarding automation** | Rich customer-enablement docs (onboarding playbook, champion guide, go-live plan); self-service onboarding not built | **Docs strong; automation partial** (Phase 8 CFB / SUP items) |
| **Customer success metrics** | No live customers | **NOT AVAILABLE — not launched** |

## Findings

- **COM-01 (MEDIUM):** No licensing/entitlement enforcement (feature gating, seat/tenant
  limits, plan tiers). Needed for commercial SaaS packaging.
- **COM-02 (HIGH, inherited):** SaaS go-live is gated by the same 1 CRITICAL + 8 HIGH —
  a paid multi-tenant SaaS **cannot onboard customers with SEC-C-01 open** (cross-tenant
  injection risk) or without incident response/alerting.
- **COM-03 (MEDIUM):** Billing path (`billing.stripe_webhook`) shares the SEC-C-01
  fail-open webhook defect — revenue integrity + tenant safety both implicated.
- **COM-04 (OBSERVATION):** No published SLA/support-tier model (ties Phase 5 SUP-02).

## Assessment

The **multi-tenant core is genuinely commercial-grade** (isolation enforced and
tested), and enablement documentation is strong. But **commercial launch is blocked**
by the release-blocking security/operability conditions and by missing
licensing/billing-enforcement and SLA/support machinery. Pricing and customer-success
metrics are **NOT AVAILABLE** because there are no customers. Commercial readiness =
**foundations strong, go-live gated.**
