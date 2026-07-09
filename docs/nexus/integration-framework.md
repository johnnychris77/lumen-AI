# Project Nexus — Integration Framework

LumenAI v3.2

## Mission

Transform LumenAI into an enterprise integration platform that securely
connects with hospital systems while preserving tenant isolation,
auditability, and clinical governance. **LumenAI enriches external data
with anatomy-aware clinical intelligence. It does not become the system
of record for every workflow.**

## Not a second integration stack

This codebase already has a substantial P17 "Healthcare Quality & Safety
Ecosystem Integration" layer — `app/models/integrations.py`,
`app/routes/integrations.py` (prefix `/api/integrations`), and
`app/services/connectors/` (`BaseConnector` ABC, CSV connectors for
CensiTrac/SPM, plus IP/quality-safety/SPD connectors) — covering CSV/API
import of clinical tracking, quality/safety, and infection-prevention data
for correlation and quality analysis, with its own nightly scheduler
(`app/services/integration_scheduler.py`).

Project Nexus is a different axis, not a duplicate:

| | P17 (`app/models/integrations.py`) | Nexus (`app/models/nexus_integration.py`) |
|---|---|---|
| Purpose | Clinical data import for correlation/quality analysis | Platform integration framework: registry, versioning, sync, identity, events, gateway |
| Scope | CensiTrac, SPM, ReadySet, Abacus, VendorMade, SafeCare, RLDatix, MIDAS, Verge, ICNet, VigiLanz, Theradoc, Epic/Cerner/Meditech (roadmap) | CensiTrac, SPM, Epic, Cerner, Oracle ERP, SAP, CMMS, Active Directory, SSO (OIDC/SAML) |
| Records | PHI-stripped clinical/quality/IP event records, quarantined on error | Instrument/tray asset records, work-queue links, identity mappings, typed events |

Where the same named system appears in both (CensiTrac, SPM), Nexus's
adapters (`app/services/nexus_connectors/adapters.py`) reuse the existing
`CensiTracCSVConnector`/`SPMCSVConnector` for the actual parsing rather
than re-implementing it — see `connector-sdk.md`.

## Architecture

```
backend/app/models/nexus_integration.py          — 9 tables + catalog/enum constants
backend/app/services/nexus_registry_service.py    — Section 1 & 2: registry, versioning
backend/app/services/nexus_credential_service.py  — Section 10: API-key issuance/auth
backend/app/services/nexus_health_service.py      — Section 1 & 8: health, error log, monitoring
backend/app/services/nexus_asset_sync_service.py  — Section 3 & 9: instrument/tray sync
backend/app/services/nexus_work_queue_sync_service.py — Section 4: work-queue links
backend/app/services/nexus_identity_service.py    — Section 5: role mapping
backend/app/services/nexus_event_bus_service.py   — Section 6: event bus
backend/app/services/nexus_connectors/            — Section 2: per-vendor adapters
backend/app/routes/nexus_integration.py           — /api/nexus/*
backend/app/routes/nexus_api_gateway.py           — /api/v1/* (see api-gateway.md)
frontend/src/components/NexusDashboard.tsx
frontend/src/pages/NexusPage.tsx                  — route: /integrations
```

## The Connector Registry (Section 1)

`NexusConnector` is a tenant's registered, versioned instance of a static
catalog entry (`NEXUS_CONNECTOR_CATALOG`). Registering a connector never
requires touching core routing or scheduling — the catalog and the
`app/services/nexus_connectors/adapters.py::get_adapter()` factory are the
only two places a *future* connector type needs to be added. Every
`NexusConnector` row tracks:

- **Connection health** — `health_status` (healthy/degraded/error/unknown),
  computed from `consecutive_errors` and sync staleness
  (`nexus_health_service.compute_health_status`).
- **Authentication** — `auth_type` plus whether an active
  `NexusConnectorCredential` exists (see `data-governance.md` /
  `integration-security` in this doc for the credential lifecycle).
- **Retry logic** — every sync (`NexusSyncRun`) carries `attempt_number` /
  `max_attempts`; a sync that raises is marked `retrying` until attempts
  are exhausted, then `failed`.
- **Scheduling** — a connector can be driven manually via
  `POST /connectors/{id}/sync/assets` or `/sync/work-queue`, or wired into
  the same `BackgroundScheduler` pattern P17's
  `integration_scheduler.py::register_integration_scheduler` already
  established, once a real per-vendor pull schedule is configured.
- **Error logging** — every sync failure writes a `NexusConnectorErrorLog`
  row (`GET /connectors/{id}/errors`).
- **Versioning** — `version` is set at registration from the catalog's
  `default_version` and can be bumped explicitly
  (`POST /connectors/{id}/version`) as an adapter implementation evolves.

## Integration Security (Section 10)

- **API keys** — issued via `nexus_credential_service.issue_credential`,
  which reuses the exact `secrets.token_urlsafe(40)` + SHA-256-hash-only
  pattern already established twice in this codebase
  (`routes/capture.py`'s device registration,
  `routes/p25_infrastructure.py::issue_api_credential`). The raw key is
  returned exactly once, at issuance, and is never stored or retrievable
  again.
- **OAuth2 / OIDC** — see `identity-integration.md`; OIDC verification
  reuses the existing production-capable `app/auth/jwks_validator.py`.
- **TLS** — terminated at the platform's ingress, as for every other route
  in this codebase; not a Nexus-specific concern.
- **Audit logging** — every connector registration, credential issuance/
  revocation, and asset sync is logged via `app/audit.py::log_audit_event`.
- **Least privilege** — role resolution defaults to `viewer` when no
  identity mapping matches (`identity-integration.md`); the API gateway
  itself defaults every unauthenticated request to a 401, never an
  implicit tenant.
- **Encrypted secrets** — only a SHA-256 hash is ever persisted; nothing
  in this codebase can recover a raw API key after issuance.
- **Connector isolation** — every adapter subclass in
  `nexus_connectors/adapters.py` is independent; a change to one vendor's
  logic cannot affect another's, and every sync method operates strictly
  within the tenant scope passed to it.

## Never fabricate

Every honest-scoping decision in Nexus follows one rule: if a connector
hasn't actually been given real data (or a real credential), it reports
zero records / "not configured" rather than inventing something. This is
enforced structurally — `sync_assets`/`sync_work_queue_link` only ever
process what's passed to them, and work-queue links are refused for any
`internal_ref_id` that doesn't correspond to a real internal record.
