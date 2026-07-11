# Project Infinity — Developer Platform

LumenAI OS v5.0, Sections 1 & 2.

## Naming disambiguation

Infinity is the 19th additive sprint, and the widest in surface area
(platform, marketplace, billing, security). Every existing platform/
marketplace/billing/API-versioning system was read in full before writing
any code:

| Concern | Pre-existing system | Infinity's relationship to it |
|---|---|---|
| App/plugin registry | Genesis's `PlatformModule`/`PlatformModuleLicense`/`PlatformPlugin` (v4.0) | `PlatformPlugin` extended additively (5 new extension-point columns); `PlatformModuleLicense` reused as-is for Module Licensing |
| Workflow marketplace | Forge's `WorkflowDefinition.marketplace_status` (v4.1) | Reused only for its exact `private/pending_review/published` naming — a new, generic `MarketplaceListing` model, not a second use of Forge's table |
| Versioned public API | Nexus's `/api/v1/*` gateway (v3.2) | Extended directly with 12 new endpoints — no second versioned gateway |
| Secret API keys | `nexus_credential_service.py`'s hash-only pattern | Reused verbatim for `DeveloperApiKey` |
| Certification approval | Forge's `WorkflowApprovalChain` (v4.1), already reused by Athena/Phoenix | Reused a third time with 7 named gates |
| Third-party identity | `TenantMembership` (internal only) | New `DeveloperAccount`, deliberately distinct |
| Billing | P14's inspection-volume `TenantPlan`/`PaymentEvent` | Module Licensing reuses Genesis; Enterprise/Partner licensing and revenue sharing are genuinely new (`PartnerLicense`, `MarketplaceRevenueEvent`) |
| Sandbox | v1.9's `pilot_config.py` (a different, older sales-pilot concept) | Genuinely new `DeveloperSandboxSession` |

## Developer Portal (Section 1)

Frontend route `/developers`. Composes:

* **API Explorer** — a documented catalog of every `/api/v1/*` endpoint (mirrors `nexus_api_gateway.py`; kept in sync manually, not dynamically introspected, to avoid a routes↔service circular import).
* **Rate Limits** — a fixed, documented policy (sandbox vs. certified-partner tiers). This platform has no live per-key request-metering infrastructure, so this is never presented as a real-time counter.
* **Tutorials** — a fixed reference list.
* **Authentication** — `DeveloperAccount`/`DeveloperApiKey`, admin-provisioned (see below).
* **Sandbox Environment** — see `docs/infinity/certification.md`.

```
GET /api/infinity/developer-portal/api-explorer
GET /api/infinity/developer-portal/rate-limits
GET /api/infinity/developer-portal/tutorials
GET /api/infinity/developer-portal/me   (developer-API-key authenticated)
```

### Two distinct auth paths

Internal tenant staff use `tenant_authz.require_tenant_roles` (real
`TenantMembership` verification), matching Athena (v4.8) and Phoenix
(v4.9). Third-party developers authenticate with a `DeveloperApiKey` via
the `X-Infinity-Developer-Key` header — a genuinely separate identity
path, since a developer building an app is not necessarily tenant staff.
Account creation and API-key issuance are **admin-gated, not open
self-service** — matching the brief's "trusted third parties" framing.

```
POST /api/infinity/developer-accounts
POST /api/infinity/developer-accounts/{id}/api-keys
```

## Public Platform APIs (Section 2)

`nexus_api_gateway.py`'s `/api/v1/*` router is extended (not duplicated)
with the remaining named systems, using the exact same
`require_gateway_auth` dependency (bearer token or `X-Nexus-Api-Key`) as
its five pre-existing endpoints:

```
GET /api/v1/identity        GET /api/v1/organizations   GET /api/v1/users
GET /api/v1/analytics       GET /api/v1/pulse           GET /api/v1/sentinel
GET /api/v1/forge           GET /api/v1/catalyst        GET /api/v1/orbit
GET /api/v1/apollo          GET /api/v1/athena          GET /api/v1/phoenix
```

Each composes its real, already-built summary function (e.g. `/api/v1/phoenix`
calls `phoenix_learning_engine_service.learning_engine_summary`) — no
re-derivation of any module's own logic.
