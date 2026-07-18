# Audit Actor Attribution Specification (LPZ-DIR-002, Phase 6)

## Single actor-attribution contract

Every security-relevant audit event should carry:

| Field | Source |
|---|---|
| timestamp | server clock (UTC) |
| actor_user_id | principal.user_id (0 until user-id resolution lands) |
| actor_subject | principal.subject |
| actor_email | principal.email |
| actor_role | principal.role (server-resolved, never a header) |
| tenant_id | verified TenantScope.tenant_id |
| authentication_method | principal.authentication_method (development/jwt/oidc) |
| action / object_type / object_id | call site |
| request_id / correlation_id | request middleware |
| source_ip | where permitted by policy |
| outcome / reason | success \| failure + detail |
| before / after state | for mutations, where meaningful |
| hash / integrity reference | existing hash-chain (enterprise_audit_service) |

## Requirements and current state

* **Authenticated users must not be recorded as `unknown`.** Today
  `enterprise_auth.get_request_actor` falls back to `"unknown"` from
  headers (Finding F6). The typed principal now supplies a verified
  `email`/`subject`/`authentication_method`; audit call sites should read
  these from the principal instead of the header.
* **Development actors visibly labeled:** `authentication_method ==
  "development"` distinguishes them; audit `details` should include it.
* **Failed authorization must be auditable:** 401/403 on tenant-scoped
  routes should emit a `failure` audit event (action e.g.
  `tenant_access_denied`). Wiring this into `resolve_verified_tenant`'s
  403 paths is part of the next increment.
* **Never log** raw access tokens, secrets, or unnecessary sensitive
  data. The existing writer already stores only `details` (no token
  material); this spec forbids adding any.

## Disposition

The **contract** is specified here and is satisfiable by the typed
principal (which now carries verified actor fields). **Wiring** every
audit call to attribute from the principal, and emitting
authorization-failure audit events, is DEFERRED to increment 2 — it
touches many call sites and must not be bundled into the tenant-isolation
PR (execution rule: do not combine unrelated cleanup). This increment
does not regress attribution: it strictly *adds* verified actor fields to
the principal that audit can consume.
