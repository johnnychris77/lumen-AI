# ADR-0007: Tenant Isolation Model

## Status
Accepted, with two open findings from this review.

## Context
LumenAI is multi-tenant (multiple hospitals/health systems on one platform) with a hard non-negotiable constraint: tenants can never see each other's raw data. This needed a consistent enforcement mechanism across ~193 route files rather than per-route ad hoc checks.

## Decision
`require_tenant_roles(*roles)` (`app/tenant_authz.py`) is the standard dependency: it resolves caller identity from a JWT/dev-token (never a client header), resolves `tenant_id`/`tenant_name` from request headers, and requires a matching, enabled `TenantMembership` row before checking role membership — 403 otherwise. 635 call sites across the route layer use this dependency. Cross-tenant intelligence sharing (Horizon, P20, P23, P24) is handled separately via anonymization and k-anonymity thresholds (e.g. n≥10 for P23 aggregates), not by relaxing per-tenant isolation.

## Consequences
- **Positive**: pervasive, consistent adoption (635 sites) of one enforcement mechanism rather than fragmented per-route logic.
- **Open finding (Technical Debt Register TD-11)**: 18 route files use the simpler `get_current_user` dependency instead, which does not automatically enforce tenant membership — isolation on those routes depends on manual query-scoping discipline. Needs per-file confirmation that this is intentional.
- **Open finding (Technical Debt Register TD-16)**: the dev-token bypass this dependency (and `deps.py` generally) supports is gated by `APP_ENV != production`, but `APP_ENV` defaults to `"development"` if unset — a configuration-drift risk that could defeat tenant isolation entirely in a misconfigured production deployment. This is the most safety-critical open item from this entire review.
