# Project Nexus — Connector SDK

LumenAI v3.2 — Section 2

## Interfaces, not a monolith

`app/services/nexus_connectors/base.py::NexusConnectorAdapter` extends the
existing `BaseConnector` ABC
(`app/services/connectors/base_connector.py`) rather than introducing a
second interface for connectors to implement. Every Nexus adapter is still
a `test_connection()` / `preview_import()` / `run_import()` implementation
— any code already written against `BaseConnector` (the nightly scheduler,
the correlation service) keeps working unmodified against a Nexus adapter.

```python
class NexusConnectorAdapter(BaseConnector):
    connector_key: str = ""

    def __init__(self, tenant_id, facility_id, config, *, has_credential=False):
        ...

    def test_connection(self) -> dict:
        """Honestly reports {"success": False, ...} if no credential has
        ever been issued — never claims a connection it can't verify."""

    def preview_import(self, limit=10) -> dict: ...
    def run_import(self, since_timestamp=None) -> dict: ...
```

## Ten adapters, one per supported system

`app/services/nexus_connectors/adapters.py`:

| Adapter | Connector key | Reuses |
|---|---|---|
| `CensiTracAdapter` | `censitrac` | Delegates `preview_import`/`run_import` to the existing `CensiTracCSVConnector` (`app/services/connectors/csv_connector.py`) — the CSV parsing logic is not re-implemented. |
| `SPMAdapter` | `spm` | Delegates to the existing `SPMCSVConnector`. |
| `EpicAdapter` | `epic` | New. SMART on FHIR client registration is a deployment-time concern; the adapter provides the uniform sync surface Nexus routes call once that's configured. |
| `CernerAdapter` | `cerner` | New. |
| `OracleERPAdapter` | `oracle_erp` | New. |
| `SAPAdapter` | `sap` | New. |
| `CMMSAdapter` | `cmms` | New. |
| `ActiveDirectoryAdapter` | `active_directory` | New — see `identity-integration.md`. |
| `SSOOIDCAdapter` | `sso_oidc` | Connector-level connectivity only; per-request OIDC auth uses the existing `app/auth/jwks_validator.py`. |
| `SSOSAMLAdapter` | `sso_saml` | New, config + claims-mapping only — see `identity-integration.md` for exact scope. |

`get_adapter(connector_key, tenant_id, facility_id, config, has_credential=False)`
is the one factory function every caller uses — callers never import a
concrete adapter class directly, so adding an eleventh connector never
requires changing a call site, only:

1. Add one entry to `NEXUS_CONNECTOR_CATALOG` (`app/models/nexus_integration.py`).
2. Add one adapter subclass and one `_ADAPTER_CLASSES` entry
   (`adapters.py`).

No core routing, registry, health, or scheduling code changes — this is
what "future connectors can be enabled without changing core architecture"
means concretely in this codebase.

## Vendor isolation

Every adapter subclass is independent. `CensiTracAdapter` holds its own
`CensiTracCSVConnector` instance; a bug or vendor-format change in one
adapter cannot leak into another's behavior, since none of them share
mutable state, a base implementation with vendor-specific branching, or a
shared parsing routine beyond the trivial `test_connection` default.

## What the SDK does not do

Adapters do not perform live outbound network calls to the named vendor
systems in this repository — this is a demo/development environment, and
a stub that "successfully" fabricated Epic/Cerner/ERP/CMMS data would
violate this platform's "never fabricate data" rule. `run_import`/
`preview_import` on the six new adapters (Epic, Cerner, Oracle ERP, SAP,
CMMS, Active Directory) return the honest, empty `BaseConnector` default
until wired to a real client library and real deployment credentials.
What's fully implemented and tested is everything downstream of "the
connector received real data": upsert, conflict detection, Digital Twin
linking, and provenance (`nexus_asset_sync_service.py`, exercised via
`POST /api/nexus/connectors/{id}/sync/assets` with an
`external_records` payload).
