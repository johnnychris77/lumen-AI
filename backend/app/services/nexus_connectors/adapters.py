"""v3.2 — Project Nexus, Section 2: per-vendor connector adapters.

One class per supported system, each isolated so a change to one vendor's
integration never touches another's — exactly the "adapters ... vendor-
specific implementations remain isolated" requirement. CensiTrac and SPM
reuse the existing CSV connectors (`app/services/connectors/csv_connector.py`)
for the actual parsing logic rather than re-implementing it; the rest are
new adapters for connector types this codebase didn't have before.
"""
from __future__ import annotations

from app.models.nexus_integration import NEXUS_CONNECTOR_KEYS
from app.services.connectors.csv_connector import CensiTracCSVConnector, SPMCSVConnector
from app.services.nexus_connectors.base import NexusConnectorAdapter


class CensiTracAdapter(NexusConnectorAdapter):
    connector_key = "censitrac"

    def __init__(self, tenant_id: str, facility_id: str, config: dict, *, has_credential: bool = False):
        super().__init__(tenant_id, facility_id, config, has_credential=has_credential)
        self._delegate = CensiTracCSVConnector(tenant_id, facility_id, config)

    def preview_import(self, limit: int = 10) -> dict:
        return self._delegate.preview_import(limit=limit)

    def run_import(self, since_timestamp=None) -> dict:
        return self._delegate.run_import(since_timestamp=since_timestamp)


class SPMAdapter(NexusConnectorAdapter):
    connector_key = "spm"

    def __init__(self, tenant_id: str, facility_id: str, config: dict, *, has_credential: bool = False):
        super().__init__(tenant_id, facility_id, config, has_credential=has_credential)
        self._delegate = SPMCSVConnector(tenant_id, facility_id, config)

    def preview_import(self, limit: int = 10) -> dict:
        return self._delegate.preview_import(limit=limit)

    def run_import(self, since_timestamp=None) -> dict:
        return self._delegate.run_import(since_timestamp=since_timestamp)


class EpicAdapter(NexusConnectorAdapter):
    """Epic (SMART on FHIR). OAuth2/EHR-launch flows are a deployment-time
    concern (real client registration with a hospital's Epic instance) —
    this adapter provides the uniform sync surface Nexus routes call
    against once that's configured."""
    connector_key = "epic"


class CernerAdapter(NexusConnectorAdapter):
    connector_key = "cerner"


class OracleERPAdapter(NexusConnectorAdapter):
    connector_key = "oracle_erp"


class SAPAdapter(NexusConnectorAdapter):
    connector_key = "sap"


class CMMSAdapter(NexusConnectorAdapter):
    connector_key = "cmms"


class ActiveDirectoryAdapter(NexusConnectorAdapter):
    connector_key = "active_directory"


class SSOOIDCAdapter(NexusConnectorAdapter):
    """OIDC login plugs into the already production-capable
    `app/auth/jwks_validator.py` (signature verification) and
    `app/auth/jwt_validator.py` (claims mapping) — this adapter only
    reports connector-level connectivity, not per-request auth, which
    stays on the existing OIDC auth path."""
    connector_key = "sso_oidc"


class SSOSAMLAdapter(NexusConnectorAdapter):
    """SAML has no prior art in this codebase. This adapter is config +
    claims-mapping only — it does not perform its own XML-signature
    cryptographic verification of a SAML assertion; see
    docs/nexus/identity-integration.md for the exact scope."""
    connector_key = "sso_saml"


_ADAPTER_CLASSES: dict[str, type[NexusConnectorAdapter]] = {
    "censitrac": CensiTracAdapter,
    "spm": SPMAdapter,
    "epic": EpicAdapter,
    "cerner": CernerAdapter,
    "oracle_erp": OracleERPAdapter,
    "sap": SAPAdapter,
    "cmms": CMMSAdapter,
    "active_directory": ActiveDirectoryAdapter,
    "sso_oidc": SSOOIDCAdapter,
    "sso_saml": SSOSAMLAdapter,
}


def get_adapter(connector_key: str, tenant_id: str, facility_id: str, config: dict, *, has_credential: bool = False) -> NexusConnectorAdapter:
    if connector_key not in _ADAPTER_CLASSES:
        raise ValueError(f"connector_key must be one of {NEXUS_CONNECTOR_KEYS}")
    adapter_cls = _ADAPTER_CLASSES[connector_key]
    return adapter_cls(tenant_id, facility_id, config, has_credential=has_credential)
