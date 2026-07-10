# Project Genesis — Platform Administration

LumenAI OS v4.0 — Section 9

## Composes every existing admin surface — adds none new for what already exists

`platform_admin_service.py` and the `/platform-admin` console read
directly from the system that already owns each kind of data:

| Sprint's requirement | Source |
|---|---|
| Organizations | `platform_org_service.organization_tree` — P16's existing enterprise hierarchy |
| Licenses | `platform_licensing_service` — new this sprint (the module concept itself is new) |
| Modules | `platform_module_registry_service` |
| Users | `app.models.user.User`, read directly (`hashed_password` never included in the response) |
| Roles | `platform_identity_service.list_known_roles` |
| Feature Flags | `app.models.feature_flag.FeatureFlag`, the same table `app/routes/entitlements.py::create_flag`/`get_flags` already reads/writes — no second flag store |
| API Keys | `app.models.p25_infrastructure.IndustryAPICredential`, the existing hash-only credential store (`api_key_hash` never included in the response) — issuance still goes through its existing route in `app/routes/p25_infrastructure.py`, which already implements the `secrets.token_urlsafe(40)` / SHA-256-hash-only / shown-once pattern this codebase's security constraints require |
| Integrations | `app.services.nexus_registry_service.list_connectors` |
| Audit Logs | `app.models.audit_log.AuditLog` |

## Endpoints

```
GET /api/platform/admin/dashboard        — composed overview (all sections above)
GET /api/platform/admin/users
GET /api/platform/admin/feature-flags
GET /api/platform/admin/api-keys
GET /api/platform/admin/integrations
GET /api/platform/admin/audit-logs
```

All `/admin/*` endpoints require the `admin` role
(`require_roles("admin")`) — no other role in the canonical catalog can
read the Platform Administration console.

## Frontend

`/platform-admin` (`PlatformAdminPage.tsx` → `PlatformAdminDashboard.tsx`)
presents these eight sections as tabs, with per-module license
enable/disable actions calling `POST /api/platform/licenses` directly
(audited via `platform.license_changed`, published to the event bus as
`ModuleLicenseChanged`).
