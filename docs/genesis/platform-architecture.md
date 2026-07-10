# LumenAI OS v4.0 — Platform Architecture

Codename: Project Genesis

## Why `docs/genesis/`, not `docs/platform/`

A `docs/platform/` folder already exists in this repository — it holds
operations runbooks (`database-runbook.md`, `environment-strategy.md`,
`production-readiness-checklist.md`, `security-operations.md`) unrelated
to this sprint. Rather than conflate an unrelated existing doc set with
this sprint's docs, Genesis's documentation lives in `docs/genesis/`,
following the same flat, sprint-name convention every other sprint uses
(`docs/sentinel/`, `docs/atlas/`, `docs/nexus/`, `docs/insight/`,
`docs/horizon/`, `docs/beacon/`).

## Composition, not a rewrite

Genesis is the tenth cross-cutting sprint built on this branch. Its
mission — "transform LumenAI from a single application into a modular
operating system" — is achieved the same way every one of the prior nine
sprints achieved their own transformative-sounding mission: additively.
No existing engine, route, model, or page is deleted, moved, or
rewritten. Concretely:

| Platform Core capability | Implementation |
|---|---|
| Identity | `platform_identity_service.py` — read-only union of the four existing authz systems (`app/authz.py`, `app/enterprise_auth.py`, `app/auth/context.py::role_to_permissions`, Atlas's `EnterpriseRoleAssignment`) |
| RBAC | Same as above — every existing `require_roles(...)` call site is untouched |
| Tenant Management | `platform_org_service.py` reads P16's existing `tenant_id`-scoped `EnterpriseFacility` |
| Organization Management | `platform_org_service.py` reads P16's existing `HealthSystem → Market → Region → Facility → Department` hierarchy directly — no second hierarchy |
| Feature Flags | Reuses `app/models/feature_flag.py` / `app/entitlements.py` directly |
| Licensing | `platform_licensing_service.py` + new `PlatformModuleLicense` table — the *module* concept is new this sprint, so there was nothing to extend for per-module licensing specifically; `app/entitlements.py`'s plan/feature-flag resolution is untouched |
| Audit Engine | Reuses `app/audit.py::log_audit_event` / `AuditLog` directly |
| Notification Engine | `platform_notification_service.py` composes the three existing notification tables (`CaseNotification`, `WorkflowNotification`, `MobileNotification`) into one read-only feed |
| Event Bus | Reuses Nexus's `nexus_event_bus_service.publish` / `NexusEvent`, extended with two new event types (`ModuleLicenseChanged`, `PluginRegistered`) |
| Configuration | New `PlatformConfiguration` key/value table — genuinely didn't exist before (only narrow single-purpose config tables like `TenantSSOConfig` did) |

Every genuinely new table in this sprint (`PlatformModule`,
`PlatformModuleLicense`, `PlatformConfiguration`, `PlatformPlugin`,
`PlatformFavoriteModule`, `PlatformRecentModule`) exists because the
concept it models (a first-class application module, a per-tenant module
license, a generic config store, a plugin registration record, per-user
launcher personalization) genuinely did not exist anywhere in this
codebase before Genesis — confirmed by an explicit research pass before
any code was written (see the "reuse map" comment at the top of
`app/models/platform_core.py`).

## API surface

All Platform Core endpoints live under `/api/platform/*`
(`app/routes/platform.py`). See `docs/genesis/identity.md`,
`docs/genesis/navigation.md`, `docs/genesis/shared-services.md`,
`docs/genesis/plugin-framework.md`, and `docs/genesis/platform-admin.md`
for section-by-section detail.

## Definition of Done, honestly stated

"LumenAI is no longer a single application" is true in the sense this
sprint actually delivers: every existing application module is now
described, licensed, permission-gated, searchable, and discoverable
through one shared Platform Core, and any future module can register
itself (Section 8) without modifying this core. It is not true in the
sense of "every existing engine now lives in a physically separate
deployable package" — that would be a much larger, higher-risk
undertaking than a single sprint safely supports on a 2800+ test,
174+ file production codebase, and was not attempted here.
