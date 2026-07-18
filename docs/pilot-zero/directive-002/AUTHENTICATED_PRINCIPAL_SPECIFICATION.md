# Authenticated Principal Specification (LPZ-DIR-002, Phase 2)

## Contract

`app/security/principal.py :: AuthenticatedPrincipal` (frozen dataclass).

| Field | Type | Source | Validation |
|---|---|---|---|
| subject | str | JWT `sub` / dev synthetic email | required, non-empty |
| email | str | same as subject | required |
| username | str | same | may equal email |
| role | str | `auth_simple._user_role(sub)` (server-side table) or dev token→role map | never from a client header |
| authentication_method | str | `development` \| `jwt` \| `oidc` \| `demo` | set by the auth path |
| user_id | int | 0 today (see limitation) | — |
| tenant_memberships | tuple[TenantMembershipView] | `tenant_memberships` table, filtered `is_enabled=True`, keyed by verified email | DB only; never a header |
| active_tenant_id | str \| None | the single membership tenant, else None (multi-tenant needs explicit per-request selection) | must be in `tenant_memberships` to be honored |
| token_id / issued_at / expires_at | str/int \| None | JWT `jti`/`iat`/`exp` | informational |

Backward-compatible aliases: `.id` → `user_id`; `.tenant_id` →
`active_tenant_id` (so pre-existing `getattr(user, "tenant_id", None)`
call sites receive a **verified** value instead of always None).

## Source of each field

Identity comes only from a **verified credential**: a dev token present
in the server-side `_DEV_ROLE_MAP` (dev only) or an app-signed JWT whose
signature verified against the app secret (`app.deps._decode_jwt`).
Tenant authority comes only from the `tenant_memberships` table. **No
field is populated from a client identity header.**

## Validation / failure behavior

* Missing/blank bearer → 401.
* Unverifiable token → 401.
* Membership lookup failure (e.g. table missing) → empty memberships
  (fail closed): the principal exists but has no tenant, so any
  tenant-scoped route that calls `resolve_verified_tenant` returns 403
  rather than granting access.

## Development vs production

* Development principals set `authentication_method="development"` and
  are visibly labeled (`is_development is True`); dev emails are
  `{role}@local.dev`.
* Dev auth is **disabled in production**: `_DEV_AUTH_ACTIVE` is
  `ENABLE_DEV_AUTH and APP_ENV not in {production,prod}`; in production
  the dev-token branch is never taken and `_DEV_ROLE_MAP` is empty.
  Verified by `TestDevAuthDisabledInProduction`.

## Migration considerations / known limitations

* `user_id` is 0 until a stable per-user id is resolvable from `sub`
  (users table lookup) — DEFERRED; nothing in this increment relies on a
  non-zero id.
* Two auth code paths remain (`deps.get_current_user`,
  `enterprise_auth.get_auth_context`). They now share the
  membership-verified-tenant intent but are not yet unified; unification
  is architecturally significant and DEFERRED (Finding F5).
* The multi-tenant `active_tenant_id` (a user in >1 tenant) is
  intentionally None until a route selects a tenant and it is verified
  by `resolve_verified_tenant` — never guessed.
