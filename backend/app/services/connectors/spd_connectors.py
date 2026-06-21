"""P17 SPD (Sterile Processing Department) connector stubs."""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta

from app.services.connectors.base_connector import BaseConnector

PHI_PROHIBITED = frozenset({"patient_id", "mrn", "dob", "patient_name", "ssn", "name"})


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def _ts(rng: random.Random, days_ago_max: int = 30) -> str:
    offset = timedelta(days=rng.randint(0, days_ago_max), hours=rng.randint(0, 23))
    return (datetime.utcnow() - offset).isoformat()


class CensiTracConnector(BaseConnector):
    """CensiTrac SPD connector — instrument checkout/checkin, tray tracking, sterilization."""

    SYSTEM_NAME = "censitrac"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        latency = rng.randint(20, 150)
        return {"success": True, "message": "Demo connection OK", "latency_ms": latency}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        event_types = ["checkout", "checkin", "sterilization", "inspection"]
        records = []
        for i in range(min(limit, 4)):
            records.append({
                "source_system": self.SYSTEM_NAME,
                "source_record_id": f"CT-{rng.randint(10000, 99999)}",
                "source_event_type": rng.choice(event_types),
                "event_timestamp": _ts(rng),
                "instrument_id": f"INST-{rng.randint(1000, 9999)}",
                "udi": f"(01)0{rng.randint(10000000000000, 99999999999999)}",
                "barcode": f"BC{rng.randint(100000, 999999)}",
                "tray_id": f"TRAY-{rng.randint(100, 999)}",
                "sterilization_status": rng.choice(["pass", "pending", "pass"]),
                "vendor_id": f"VEND-{rng.randint(10, 99)}",
                "facility_id": self.facility_id or "main",
            })
        return {"records": records, "total_available": rng.randint(200, 800), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        imported = rng.randint(50, 300)
        return {"imported": imported, "failed": 0, "errors": []}


class SPMConnector(BaseConnector):
    """SPM (Surgical Process Management) connector — instrument tracking, cycle records."""

    SYSTEM_NAME = "spm"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = []
        for i in range(min(limit, 4)):
            records.append({
                "source_system": self.SYSTEM_NAME,
                "source_record_id": f"SPM-{rng.randint(10000, 99999)}",
                "source_event_type": rng.choice(["checkout", "checkin", "sterilization"]),
                "event_timestamp": _ts(rng),
                "instrument_id": f"INST-{rng.randint(1000, 9999)}",
                "barcode": f"SPM{rng.randint(100000, 999999)}",
                "tray_id": f"TRAY-{rng.randint(100, 999)}",
                "sterilization_status": rng.choice(["pass", "pass", "fail"]),
                "facility_id": self.facility_id or "main",
            })
        return {"records": records, "total_available": rng.randint(100, 600), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(40, 200), "failed": 0, "errors": []}


class ReadySetConnector(BaseConnector):
    """ReadySet connector — surgical readiness, loaner instrument tracking."""

    SYSTEM_NAME = "readyset"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = []
        for i in range(min(limit, 3)):
            records.append({
                "source_system": self.SYSTEM_NAME,
                "source_record_id": f"RS-{rng.randint(10000, 99999)}",
                "source_event_type": rng.choice(["checkout", "loaner_in", "loaner_out"]),
                "event_timestamp": _ts(rng),
                "instrument_id": f"LN-{rng.randint(1000, 9999)}",
                "tray_id": f"TRAY-{rng.randint(100, 999)}",
                "vendor_id": f"VEND-{rng.randint(10, 99)}",
                "sterilization_status": "pass",
                "facility_id": self.facility_id or "main",
            })
        return {"records": records, "total_available": rng.randint(50, 300), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(20, 150), "failed": 0, "errors": []}


class AbacusConnector(BaseConnector):
    """Abacus connector — instrument management, repair history."""

    SYSTEM_NAME = "abacus"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = []
        for i in range(min(limit, 4)):
            records.append({
                "source_system": self.SYSTEM_NAME,
                "source_record_id": f"AB-{rng.randint(10000, 99999)}",
                "source_event_type": rng.choice(["repair", "inspection", "checkout"]),
                "event_timestamp": _ts(rng),
                "instrument_id": f"INST-{rng.randint(1000, 9999)}",
                "udi": f"(01)0{rng.randint(10000000000000, 99999999999999)}",
                "vendor_id": f"VEND-{rng.randint(10, 99)}",
                "repair_type": rng.choice(["sharpening", "realignment", "replacement", None]),
                "repair_status": rng.choice(["sent", "returned", "scrapped"]),
                "facility_id": self.facility_id or "main",
            })
        return {"records": records, "total_available": rng.randint(30, 200), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(15, 100), "failed": 0, "errors": []}


class VendorMadeConnector(BaseConnector):
    """VendorMade connector — vendor loaner instruments, repair responses, baseline catalogs."""

    SYSTEM_NAME = "vendormade"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = []
        for i in range(min(limit, 3)):
            records.append({
                "source_system": self.SYSTEM_NAME,
                "source_record_id": f"VM-{rng.randint(10000, 99999)}",
                "source_event_type": rng.choice(["loaner_in", "repair", "catalog_update"]),
                "event_timestamp": _ts(rng),
                "instrument_id": f"VM-INST-{rng.randint(1000, 9999)}",
                "vendor_id": f"VEND-{rng.randint(10, 99)}",
                "barcode": f"VM{rng.randint(100000, 999999)}",
                "facility_id": self.facility_id or "main",
            })
        return {"records": records, "total_available": rng.randint(20, 150), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(10, 80), "failed": 0, "errors": []}
