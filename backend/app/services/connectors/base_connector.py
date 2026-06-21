"""Base connector interface for all healthcare system integrations."""
from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """Abstract base for all external system connectors."""

    def __init__(self, tenant_id: str, facility_id: str, config: dict):
        self.tenant_id = tenant_id
        self.facility_id = facility_id
        self.config = config  # non-sensitive config only
        # Credentials come from env vars or secret manager, not config dict

    @abstractmethod
    def test_connection(self) -> dict:
        """Returns {"success": bool, "message": str, "latency_ms": int}"""

    @abstractmethod
    def preview_import(self, limit: int = 10) -> dict:
        """Returns {"records": [...], "total_available": int, "sample_only": True}"""

    @abstractmethod
    def run_import(self, since_timestamp=None) -> dict:
        """Returns {"imported": int, "failed": int, "errors": [...]}"""

    def get_system_name(self) -> str:
        return self.__class__.__name__.replace("Connector", "").lower()
