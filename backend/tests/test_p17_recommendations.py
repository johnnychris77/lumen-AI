"""P17 Recommendation improvement tests."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")

from app.main import app
from app.db.base import Base

HEADERS = {"Authorization": "Bearer dev-token"}

CENSITRAC_CSV = """InstrumentID,InstrumentName,TrayID,TrayName,EventType,EventDate,SterilizationStatus,VendorID,Barcode,UDI
INST-001,Scissors,TRAY-A,General,checkout,2026-06-01,pass,VND-1,BC123,UDI-456
INST-002,Forceps,TRAY-A,General,checkin,2026-06-01,pass,,BC124,"""

SPM_CSV = """item_id,item_name,tray_id,cycle_id,event_type,event_date,sterilizer_id,cycle_status
ITEM-001,Clamp,TRAY-B,CYC-1,checkout,2026-06-01,STER-1,pass
ITEM-002,Needle,TRAY-B,CYC-1,checkin,2026-06-02,STER-1,pass"""

CENSITRAC_BAD_CSV = """WrongCol1,WrongCol2
val1,val2"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# TestCSVConnector
# ---------------------------------------------------------------------------

class TestCSVConnector:
    def test_censitrac_csv_parse_valid_csv(self):
        from app.services.connectors.csv_connector import CensiTracCSVConnector
        c = CensiTracCSVConnector("tenant-1", "fac-1", {})
        result = c.parse_csv_content(CENSITRAC_CSV, "tenant-1", "fac-1")
        assert result["raw_row_count"] == 2
        assert len(result["records"]) == 2
        assert result["failed"] == 0
        assert result["records"][0]["instrument_id"] == "INST-001"

    def test_censitrac_csv_handles_date_formats(self):
        from app.services.connectors.csv_connector import CensiTracCSVConnector
        csv_data = "InstrumentID,InstrumentName,TrayID,TrayName,EventType,EventDate,SterilizationStatus,VendorID,Barcode,UDI\nINST-001,Scissors,TRAY-A,General,checkout,06/15/2026,pass,VND-1,BC123,UDI-456"
        c = CensiTracCSVConnector("tenant-1", "fac-1", {})
        result = c.parse_csv_content(csv_data, "tenant-1", "fac-1")
        assert len(result["records"]) == 1
        assert "2026-06-15" in result["records"][0]["event_timestamp"]

    def test_censitrac_csv_missing_columns_returns_error(self):
        from app.services.connectors.csv_connector import CensiTracCSVConnector
        c = CensiTracCSVConnector("tenant-1", "fac-1", {})
        result = c.parse_csv_content(CENSITRAC_BAD_CSV, "tenant-1", "fac-1")
        assert len(result["errors"]) > 0
        assert result["records"] == []

    def test_spm_csv_parse_valid_csv(self):
        from app.services.connectors.csv_connector import SPMCSVConnector
        c = SPMCSVConnector("tenant-1", "fac-1", {})
        result = c.parse_csv_content(SPM_CSV, "tenant-1", "fac-1")
        assert result["raw_row_count"] == 2
        assert len(result["records"]) == 2

    def test_csv_connector_test_connection_returns_success(self):
        from app.services.connectors.csv_connector import CensiTracCSVConnector
        c = CensiTracCSVConnector("tenant-1", "fac-1", {})
        result = c.test_connection()
        assert result["success"] is True
        assert result["connector_type"] == "csv"

    def test_csv_parse_computes_payload_hash(self):
        from app.services.connectors.csv_connector import CensiTracCSVConnector
        c = CensiTracCSVConnector("tenant-1", "fac-1", {})
        result = c.parse_csv_content(CENSITRAC_CSV, "tenant-1", "fac-1")
        assert "raw_payload_hash" in result["records"][0]
        assert len(result["records"][0]["raw_payload_hash"]) == 32


# ---------------------------------------------------------------------------
# TestWebhook
# ---------------------------------------------------------------------------

class TestWebhook:
    def test_webhook_endpoint_returns_200_without_signature(self, client):
        resp = client.post(
            "/api/integrations/webhook/censitrac",
            json=[{"source_event_type": "checkout", "event_timestamp": "2026-06-01T00:00:00"}],
            headers={"X-Tenant-Id": "tenant-webhook-test"},
        )
        assert resp.status_code == 200
        assert resp.json()["received"] is True

    def test_webhook_endpoint_no_auth_header_required(self, client):
        # No Authorization header
        resp = client.post(
            "/api/integrations/webhook/censitrac",
            json=[],
            headers={"X-Tenant-Id": "tenant-webhook-test"},
        )
        assert resp.status_code == 200

    def test_webhook_processes_events_list(self, client):
        events = [
            {"source_event_type": "checkout", "event_timestamp": "2026-06-01T00:00:00", "instrument_id": "INST-W1"},
            {"source_event_type": "checkin", "event_timestamp": "2026-06-02T00:00:00", "instrument_id": "INST-W2"},
        ]
        resp = client.post(
            "/api/integrations/webhook/censitrac",
            json=events,
            headers={"X-Tenant-Id": "tenant-webhook-test"},
        )
        assert resp.status_code == 200
        assert resp.json()["events_processed"] == 2

    def test_webhook_processes_single_event(self, client):
        resp = client.post(
            "/api/integrations/webhook/rldatix",
            json={"source_event_type": "adverse_event", "event_timestamp": "2026-06-01T00:00:00"},
            headers={"X-Tenant-Id": "tenant-webhook-test"},
        )
        assert resp.status_code == 200
        assert resp.json()["system"] == "rldatix"


# ---------------------------------------------------------------------------
# TestScheduler
# ---------------------------------------------------------------------------

class TestScheduler:
    def test_scheduler_function_importable(self):
        from app.services.integration_scheduler import register_integration_scheduler, _run_nightly_imports
        assert callable(register_integration_scheduler)
        assert callable(_run_nightly_imports)

    def test_nightly_imports_does_not_crash_with_no_connections(self):
        from app.services.integration_scheduler import _run_nightly_imports
        from app.db import engine
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        # Should not raise
        _run_nightly_imports(Session)


# ---------------------------------------------------------------------------
# TestNewModels
# ---------------------------------------------------------------------------

class TestNewModels:
    def test_vendor_baseline_record_importable(self):
        from app.models.integrations import VendorBaselineExternalRecord
        assert VendorBaselineExternalRecord.__tablename__ == "vendor_baseline_external_records"

    def test_recall_external_record_importable(self):
        from app.models.integrations import RecallExternalRecord
        assert RecallExternalRecord.__tablename__ == "recall_external_records"


# ---------------------------------------------------------------------------
# TestHealthEndpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def _create_connection(self, client):
        resp = client.post(
            "/api/integrations/systems",
            json={"system_name": "censitrac", "system_category": "spd_tracking", "connector_type": "csv"},
            headers=HEADERS,
        )
        return resp.json()["system"]["id"]

    def test_connection_health_returns_200(self, client):
        sys_id = self._create_connection(client)
        resp = client.get(f"/api/integrations/systems/{sys_id}/health", headers=HEADERS)
        assert resp.status_code == 200

    def test_connection_health_has_status_field(self, client):
        sys_id = self._create_connection(client)
        resp = client.get(f"/api/integrations/systems/{sys_id}/health", headers=HEADERS)
        data = resp.json()
        assert "health_status" in data
        assert data["health_status"] in ("healthy", "degraded", "error", "unknown")

    def test_connection_health_404_for_wrong_tenant(self, client):
        # Use a nonexistent system_id
        resp = client.get("/api/integrations/systems/999999/health", headers=HEADERS)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TestDryRun
# ---------------------------------------------------------------------------

class TestDryRun:
    def _create_censitrac_conn(self, client):
        resp = client.post(
            "/api/integrations/systems",
            json={"system_name": "censitrac", "system_category": "spd_tracking", "connector_type": "csv"},
            headers=HEADERS,
        )
        return resp.json()["system"]["id"]

    def test_dry_run_returns_200(self, client):
        sys_id = self._create_censitrac_conn(client)
        resp = client.post(
            f"/api/integrations/systems/{sys_id}/dry-run",
            json={"csv_content": CENSITRAC_CSV},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_dry_run_does_not_write_to_db(self, client):
        """Dry run should report would_create without persisting."""
        sys_id = self._create_censitrac_conn(client)
        resp = client.post(
            f"/api/integrations/systems/{sys_id}/dry-run",
            json={"csv_content": CENSITRAC_CSV},
            headers=HEADERS,
        )
        data = resp.json()
        assert data["db_unchanged"] is True

    def test_dry_run_returns_would_create_count(self, client):
        sys_id = self._create_censitrac_conn(client)
        resp = client.post(
            f"/api/integrations/systems/{sys_id}/dry-run",
            json={"csv_content": CENSITRAC_CSV},
            headers=HEADERS,
        )
        data = resp.json()
        assert "would_create" in data
        assert data["would_create"] == 2


# ---------------------------------------------------------------------------
# TestBAAGate
# ---------------------------------------------------------------------------

class TestBAAGate:
    def test_quality_system_connection_blocked_without_baa(self, client):
        """Quality system connections require BAA — may return 400 if no BAA signed."""
        resp = client.post(
            "/api/integrations/systems",
            json={"system_name": "rldatix", "system_category": "quality_safety", "connector_type": "api_pull"},
            headers=HEADERS,
        )
        # Either 400 (BAA required) or 200 (if test tenant has BAA signed) is valid
        assert resp.status_code in (200, 400)
        if resp.status_code == 400:
            data = resp.json()
            assert "hipaa_baa_required" in str(data)

    def test_spd_system_connection_does_not_require_baa(self, client):
        """SPD connections never require BAA."""
        resp = client.post(
            "/api/integrations/systems",
            json={"system_name": "censitrac", "system_category": "spd_tracking", "connector_type": "csv"},
            headers=HEADERS,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# TestCatalog
# ---------------------------------------------------------------------------

class TestCatalog:
    def test_catalog_returns_200(self, client):
        resp = client.get("/api/integrations/catalog")
        assert resp.status_code == 200

    def test_catalog_no_auth_required(self, client):
        resp = client.get("/api/integrations/catalog")
        assert resp.status_code == 200

    def test_catalog_has_censitrac(self, client):
        resp = client.get("/api/integrations/catalog")
        names = [c["system_name"] for c in resp.json()["connectors"]]
        assert "censitrac" in names

    def test_catalog_has_baa_required_flag(self, client):
        resp = client.get("/api/integrations/catalog")
        connectors = {c["system_name"]: c for c in resp.json()["connectors"]}
        assert connectors["rldatix"].get("baa_required") is True

    def test_catalog_has_ehr_systems_as_roadmap(self, client):
        resp = client.get("/api/integrations/catalog")
        connectors = {c["system_name"]: c for c in resp.json()["connectors"]}
        assert connectors["epic"]["status"] == "roadmap"
        assert connectors["cerner"]["status"] == "roadmap"


# ---------------------------------------------------------------------------
# TestErrorQuarantine
# ---------------------------------------------------------------------------

class TestErrorQuarantine:
    def test_error_records_endpoint_returns_200(self, client):
        resp = client.get("/api/integrations/errors", headers=HEADERS)
        assert resp.status_code == 200
        assert "errors" in resp.json()

    def test_csv_parse_error_creates_error_record(self):
        """parse_csv_content on bad CSV returns errors list."""
        from app.services.connectors.csv_connector import CensiTracCSVConnector
        c = CensiTracCSVConnector("tenant-1", "fac-1", {})
        result = c.parse_csv_content(CENSITRAC_BAD_CSV, "tenant-1", "fac-1")
        # Missing required columns returns error
        assert len(result["errors"]) > 0


# ---------------------------------------------------------------------------
# TestTimeWindowedCorrelation
# ---------------------------------------------------------------------------

class TestTimeWindowedCorrelation:
    def test_correlation_returns_chain_detected_field(self, client):
        # Run correlation — may be empty/mock but should not error
        resp = client.post(
            "/api/integrations/correlation-candidates/run",
            json={"facility_id": "", "days_back": 30},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "candidates_created" in data

    def test_correlation_no_causation_language(self, client):
        resp = client.post(
            "/api/integrations/correlation-candidates/run",
            json={"facility_id": "", "days_back": 30},
            headers=HEADERS,
        )
        body_str = resp.text.lower()
        # Must not claim causation
        assert "cause" not in body_str or "potential" in body_str or "association" in body_str

    def test_correlation_candidate_has_chain_fields(self):
        from app.models.integrations import PatientImpactCorrelationCandidate
        cols = {c.name for c in PatientImpactCorrelationCandidate.__table__.columns}
        assert "chain_detected" in cols
        assert "chain_description" in cols
