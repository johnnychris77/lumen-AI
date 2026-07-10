"""v3.2 — Project Nexus, Section 2: Connector SDK base interface.

`NexusConnectorAdapter` extends the existing `BaseConnector` ABC
(`app/services/connectors/base_connector.py`) rather than introducing a
second interface — every Nexus adapter is still a `test_connection()` /
`preview_import()` / `run_import()` implementation, so it stays a drop-in
citizen of anything already written against `BaseConnector` (e.g. the
existing nightly scheduler pattern). Vendor-specific logic lives entirely
inside each adapter subclass in `adapters.py` — the registry, health,
sync, and route layers never know which vendor they're talking to.
"""
from __future__ import annotations

import time

from app.services.connectors.base_connector import BaseConnector


class NexusConnectorAdapter(BaseConnector):
    """Base for every Nexus-managed connector (Epic, Cerner, Oracle ERP,
    SAP, CMMS, Active Directory, SSO). Adds a `connector_key` identity and
    a `has_credential` flag the caller supplies (from
    `nexus_credential_service`) so `test_connection()` can honestly report
    whether the connector has ever been given a credential, rather than
    always claiming success."""

    connector_key: str = ""

    def __init__(self, tenant_id: str, facility_id: str, config: dict, *, has_credential: bool = False):
        super().__init__(tenant_id, facility_id, config)
        self.has_credential = has_credential

    def get_system_name(self) -> str:
        return self.connector_key

    def test_connection(self) -> dict:
        start = time.perf_counter()
        latency_ms = int((time.perf_counter() - start) * 1000)
        if not self.has_credential:
            return {"success": False, "message": f"No credential issued yet for '{self.connector_key}'.", "latency_ms": latency_ms}
        return {"success": True, "message": f"'{self.connector_key}' credential present.", "latency_ms": latency_ms}

    def preview_import(self, limit: int = 10) -> dict:
        return {"records": [], "total_available": 0, "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        return {"imported": 0, "failed": 0, "errors": []}
