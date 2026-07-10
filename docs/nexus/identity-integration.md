# Project Nexus — Identity Integration

LumenAI v3.2 — Section 5

## Endpoints

```
POST /api/nexus/connectors/{id}/identity-mappings
GET  /api/nexus/connectors/{id}/identity-mappings
POST /api/nexus/identity/resolve-role
```

## Supported directories

LDAP, Azure AD, Entra ID, OIDC, SAML — via the `active_directory`,
`sso_oidc`, and `sso_saml` connector types (`identity`/`sso` categories in
`NEXUS_CONNECTOR_CATALOG`).

## OIDC reuses existing, production-capable crypto

Nexus does not reimplement JWT/OIDC verification. `app/auth/jwks_validator.py`
already performs full RS256 JWKS signature verification
(`validate_jwt_signature_with_jwks`: algorithm allowlist, `kid` enforcement,
issuer/audience checks, expiration) and `app/auth/jwt_validator.py::
map_claims_to_auth_context_payload` already maps a verified token's
`groups`/`roles`/`lumenai_role` claims into an `AuthContext`. This is the
same code path `test_jwt_auth_baseline.py`/`test_jwks_integration.py`
exercise. A Nexus `sso_oidc` connector's `test_connection()` reports
connector-level connectivity (is a credential/config present); the actual
per-request login verification stays on this existing path — Nexus adds
the *group → role* mapping layer on top (see below), which didn't exist
before.

## SAML: scope, honestly stated

There is no prior SAML support anywhere in this codebase. Nexus's
`sso_saml` connector is **config and claims-mapping only** — it registers
an IdP's metadata and lets an operator map the *attribute names* an IdP
asserts (e.g. a `memberOf` attribute's group names) to LumenAI roles. It
does **not** implement its own XML-signature cryptographic verification
of a SAML `<Response>`/`<Assertion>`. A production deployment must
terminate SAML assertion validation at a real SAML Service Provider
library or an identity gateway in front of LumenAI, and pass Nexus only
the already-verified attribute claims. This limitation is stated here
deliberately rather than left implicit — Nexus does not claim to be a
complete cryptographic SAML SP.

## Role mapping (Section 5's actual deliverable)

`NexusIdentityMapping` maps one external directory/SSO group
(`external_group`) to one of six roles the sprint names —
**Technician, Supervisor, Manager, Director, Administrator, Viewer**
(`NEXUS_IDENTITY_ROLES` in `app/models/nexus_integration.py`).

This is deliberately its own six-label set, not Atlas's seven-role
`ENTERPRISE_ROLES` (`regional_administrator`, `market_director`,
`facility_director`, `spd_manager`, `supervisor`, `technician`, `viewer` —
`app/models/atlas_enterprise.py`), which exists to scope a role to a
system/market/facility node in the org hierarchy for Atlas's own RBAC.
Forcing Nexus's identity mapping onto Atlas's hierarchy-scoped roles would
conflate two different concerns (facility-scoped RBAC vs. directory-group
provisioning). The closest correspondence, for operators using both:

| Nexus identity role | Closest Atlas role |
|---|---|
| `technician` | `technician` |
| `supervisor` | `supervisor` |
| `manager` | `facility_director` |
| `director` | `regional_administrator` or `market_director` (context-dependent) |
| `administrator` | `regional_administrator` |
| `viewer` | `viewer` |

### Least privilege by default

`resolve_role_for_groups(connector_id, external_groups)` looks up mappings
for the presented groups and returns the **highest-precedence** matching
role (`administrator > director > manager > supervisor > technician >
viewer`) — a user in multiple mapped groups gets their most-privileged
applicable role, never an arbitrary or first-registered match. If **none**
of a user's groups have a mapping on file, resolution returns `viewer`
(`DEFAULT_IDENTITY_ROLE`) — never an elevated default. This is Section
10's "least privilege" requirement applied directly to provisioning, not
only to route-level RBAC.

### Auto-provisioning

`auto_provision` on a mapping is a flag an operator sets to indicate a
first-time SSO login for a user in that group should automatically create
a local account with the mapped role, rather than requiring a manual
invite — the mapping and resolution logic here is what a login flow would
call; wiring that call into the actual login route is a deployment
integration point, not part of this sprint's scope.
