# Multi-Tenant Deployment Guide

## Deployment models

LumenAI supports two deployment models, both running the same codebase:

| Model | Description | Typical customer |
|---|---|---|
| **Single-tenant** | One `tenant_id` per deployed instance (or a fixed tenant per customer database). | A large health system that wants dedicated infrastructure. |
| **Multi-tenant (shared)** | One deployment serves many facilities/customers, isolated by `tenant_id`. | A hosted/SaaS offering (the default for Community/Professional edition customers — see `docs/enterprise/commercial-packaging.md`). |

## How tenant isolation is enforced

Every table carrying clinical, operational, or governance data has a
`tenant_id` column, and every read/write route filters on it — this is
enforced at the application layer today (see
`docs/security/lumenai-enterprise-tenant-isolation-test-matrix-v1.md` for
the test matrix that verifies it) rather than at the database-row-security
layer. Concretely:

- `Inspection`, `SupervisorReview`, `PilotValidationCase`,
  `ClinicalDecisionLedgerEntry`, `CIOSEvent`, `AuditLog`, and every other
  tenant-scoped model default to `tenant_id="default-tenant"` and are
  always filtered by the authenticated user's resolved tenant
  (`app/enterprise_auth.py::get_request_tenant_id`).
- Platform `admin` role can see across tenants for legitimate cross-tenant
  operations (e.g. the network intelligence/benchmarking features,
  Phase 15/20) — always with anonymization at the point of aggregation
  (hospital identities never surface in cross-hospital intelligence, per
  the CLAUDE.md security constraint), and always audit-logged.

## Onboarding a new tenant

1. Provision the tenant record (`docs/enterprise/site-onboarding-guide.md`
   covers the operational onboarding checklist).
2. Assign an initial admin user and RBAC roles
   (`docs/security/lumenai-rbac-matrix-v1.md`).
3. Configure tenant-specific branding if applicable
   (`app/models/tenant_branding.py`).
4. Set entitlements/quotas per the customer's edition
   (`app/models/tenant_entitlement.py`, `app/models/tenant_quota.py`) —
   see `docs/enterprise/commercial-packaging.md` for edition limits.
5. Verify isolation: as the new tenant, confirm zero visibility into any
   other tenant's inspections, baselines, or dashboards.

## Capacity planning for shared multi-tenant deployments

See `docs/deployment/scaling-guide.md` for how per-tenant inspection
volume translates into database and application capacity requirements.
As a shared deployment's tenant count grows, monitor:

- Per-tenant inspection volume (via `/api/pilot-analytics/*` and
  `/api/cios/dashboard`'s throughput figures) to catch a single noisy
  tenant before it affects others.
- Database connection pool saturation — many small tenants generate many
  concurrent short-lived connections; pool sizing should account for
  tenant count, not just total request volume.

## Data residency and export

A tenant's data can be exported independently (compliance/trust-center
export routes, `app/routes/trust_center_exports.py` /
`app/routes/compliance_exports.py`) — relevant for a customer's own
data-portability requirements or for offboarding a tenant from a shared
deployment without touching any other tenant's data.
