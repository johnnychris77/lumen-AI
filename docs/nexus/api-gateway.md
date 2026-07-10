# Project Nexus — API Gateway

LumenAI v3.2 — Section 7

## The first genuinely versioned prefix in this codebase

Every existing route in this codebase is an unversioned flat prefix —
`/api/sentinel`, `/api/atlas`, `/api/integrations`, `/api/enterprise`, and
roughly sixty others. Three unrelated routes use a `/api/v1-2/...` naming
scheme (`power_bi_executive_analytics.py`, `vendor_trend_intelligence.py`,
`capa_trend_intelligence.py`) that reads like a version-bump artifact, not
real API versioning — no collision with `/api/v1/...` since the path
segments differ, but worth knowing about to avoid confusion.

`app/routes/nexus_api_gateway.py` (no feature prefix — routes are
registered at their literal `/api/v1/...` paths) is the first genuinely
versioned, stable, externally-documented API surface: a facade over
existing services, not a re-derivation of their logic.

## Endpoints

```
GET /api/v1/instruments      — this tenant's inspected-instrument inventory
GET /api/v1/inspections      — this tenant's recent inspections
GET /api/v1/digital-twins    — app/services/digital_twin_engine.compute_twin_dashboard
GET /api/v1/knowledge        — this tenant's approved KnowledgeArticle rows
GET /api/v1/enterprise       — atlas_dashboard_service.enterprise_dashboard (?system_id=)
```

Every endpoint composes an already-real query or service call — none
re-derives scoring, disposition, or knowledge-graph logic a second time.

## Authentication (Section 10)

`require_gateway_auth` accepts either:

1. **`X-Nexus-Api-Key: <raw key>`** — a connector credential issued via
   `POST /api/nexus/connectors/{id}/credentials`, matched by SHA-256 hash
   (`nexus_credential_service.authenticate_key`) — the intended path for
   machine-to-machine connector calls.
2. **`Authorization: Bearer <token>`** — the same bearer-token auth every
   other route in this codebase uses (`app.deps.get_current_user`),
   for internal/browser callers. Role is checked against the same
   `admin`/`spd_manager`/`operator`/`viewer` set every other route gates
   on.

A request with neither returns 401. A request with an expired or revoked
API key returns 401. A request with a valid bearer token but a
disallowed role returns 403 — the gateway never silently defaults to an
open tenant.

## Documented per endpoint

| Endpoint | Method | Auth | Query params | Returns |
|---|---|---|---|---|
| `/api/v1/instruments` | GET | key or bearer | `limit` (default 50) | `{api_version, tenant_id, instruments: [...]}` |
| `/api/v1/inspections` | GET | key or bearer | `limit` (default 50) | `{api_version, tenant_id, inspections: [...]}` |
| `/api/v1/digital-twins` | GET | key or bearer | `facility_id` (optional) | `{api_version, tenant_id, digital_twin: {...}}` |
| `/api/v1/knowledge` | GET | key or bearer | `limit` (default 50) | `{api_version, tenant_id, knowledge: [...]}` |
| `/api/v1/enterprise` | GET | key or bearer | `system_id` (required) | `{api_version, enterprise: {...}}` |

`/api/v1/enterprise` requires `system_id` because enterprise dashboards
are scoped to a health system (`atlas_dashboard_service.enterprise_
dashboard`), not a single tenant — a request without it returns 422
rather than guessing a system.
