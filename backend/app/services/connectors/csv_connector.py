"""CSV-based connector base — makes all SPD integrations immediately functional
since every major SPD system (CensiTrac, SPM, ReadySet, Abacus) exports CSV."""

import csv
import hashlib
import io
from datetime import datetime

from app.services.connectors.base_connector import BaseConnector


class CSVConnector(BaseConnector):
    """Base for any system that delivers data via CSV file upload or SFTP CSV drop."""

    EXPECTED_COLUMNS: list = []  # subclasses define required columns

    def test_connection(self) -> dict:
        return {
            "success": True,
            "message": f"{self.get_system_name()} CSV connector ready — upload a CSV file to begin import",
            "latency_ms": 0,
            "connector_type": "csv",
        }

    def preview_import(self, limit: int = 10) -> dict:
        """Returns schema info and expected columns for preview."""
        return {
            "connector_type": "csv",
            "expected_columns": self.EXPECTED_COLUMNS,
            "sample_only": True,
            "records": [],
            "total_available": 0,
            "message": "Upload a CSV file to preview records",
        }

    def run_import(self, since_timestamp=None) -> dict:
        return {"imported": 0, "failed": 0, "errors": [], "message": "Use parse_csv_content() to import CSV data"}

    def parse_csv_content(self, csv_content: str, tenant_id: str, facility_id: str = "") -> dict:
        """
        Parse CSV string content, validate columns, normalize rows.
        Returns: {records: [...normalized dicts], failed: int, errors: [...], raw_row_count: int}
        """
        records = []
        errors = []
        reader = csv.DictReader(io.StringIO(csv_content))

        # Validate headers
        if reader.fieldnames:
            missing = [c for c in self.EXPECTED_COLUMNS if c not in reader.fieldnames]
            if missing:
                return {
                    "records": [],
                    "failed": 0,
                    "errors": [f"Missing required columns: {missing}"],
                    "raw_row_count": 0,
                }

        raw_count = 0
        for i, row in enumerate(reader):
            raw_count += 1
            try:
                normalized = self.normalize_row(row, tenant_id, facility_id)
                if normalized:
                    # Compute payload hash for audit trail
                    row_str = str(sorted(row.items()))
                    normalized["raw_payload_hash"] = hashlib.sha256(row_str.encode()).hexdigest()[:32]
                    records.append(normalized)
            except Exception as e:
                errors.append({"row": i + 1, "error": str(e), "raw": dict(row)})

        return {
            "records": records,
            "failed": len(errors),
            "errors": errors,
            "raw_row_count": raw_count,
        }

    def normalize_row(self, row: dict, tenant_id: str, facility_id: str) -> dict:
        """Override in subclass to normalize a CSV row to a standard dict."""
        raise NotImplementedError


class CensiTracCSVConnector(CSVConnector):
    """
    Real CensiTrac CSV connector.

    CensiTrac exports instrument tracking CSVs with these standard column names.
    Column names may vary slightly by site — config can override via column_map.
    """

    EXPECTED_COLUMNS = [
        "InstrumentID", "InstrumentName", "TrayID", "TrayName",
        "EventType", "EventDate", "SterilizationStatus", "VendorID",
        "Barcode", "UDI",
    ]

    def normalize_row(self, row: dict, tenant_id: str, facility_id: str) -> dict:
        # Apply column map from config if provided (handles site-specific column names)
        col_map = self.config.get("column_map", {})

        def get(col):
            mapped = col_map.get(col, col)
            return (row.get(mapped) or row.get(col) or "").strip()

        event_date_str = get("EventDate")
        event_date = datetime.utcnow()
        if event_date_str:
            try:
                event_date = datetime.fromisoformat(event_date_str)
            except ValueError:
                for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S"):
                    try:
                        event_date = datetime.strptime(event_date_str, fmt)
                        break
                    except ValueError:
                        continue

        return {
            "tenant_id": tenant_id,
            "facility_id": facility_id,
            "source_system": "censitrac",
            "source_record_id": get("InstrumentID") or None,
            "source_event_type": get("EventType") or "tracking_record",
            "event_timestamp": event_date.isoformat(),
            "instrument_id": get("InstrumentID") or None,
            "udi": get("UDI") or None,
            "barcode": get("Barcode") or None,
            "tray_id": get("TrayID") or None,
            "sterilization_status": get("SterilizationStatus") or None,
            "vendor_id": get("VendorID") or None,
            "import_status": "imported",
            "correlation_status": "pending",
        }


class SPMCSVConnector(CSVConnector):
    EXPECTED_COLUMNS = ["item_id", "item_name", "tray_id", "cycle_id", "event_type", "event_date", "sterilizer_id", "cycle_status"]

    def normalize_row(self, row: dict, tenant_id: str, facility_id: str) -> dict:
        return {
            "tenant_id": tenant_id,
            "facility_id": facility_id,
            "source_system": "spm",
            "source_record_id": row.get("item_id", "").strip() or None,
            "source_event_type": row.get("event_type", "tracking_record").strip(),
            "event_timestamp": row.get("event_date", datetime.utcnow().isoformat()).strip(),
            "instrument_id": row.get("item_id", "").strip() or None,
            "tray_id": row.get("tray_id", "").strip() or None,
            "sterilization_status": row.get("cycle_status", "").strip() or None,
            "vendor_id": None,
            "import_status": "imported",
            "correlation_status": "pending",
        }
