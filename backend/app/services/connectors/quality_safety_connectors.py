"""P17 Quality & Safety connector stubs."""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta

from app.services.connectors.base_connector import BaseConnector


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def _ts(rng: random.Random, days_ago_max: int = 30) -> str:
    offset = timedelta(days=rng.randint(0, days_ago_max), hours=rng.randint(0, 23))
    return (datetime.utcnow() - offset).isoformat()


def _qs_record(rng: random.Random, system: str, facility_id: str) -> dict:
    """Build a de-identified quality/safety event record — no PHI fields."""
    return {
        "source_system": system,
        "source_record_id": f"{system.upper()}-{rng.randint(10000, 99999)}",
        "source_event_type": rng.choice(["adverse_event", "near_miss", "good_catch", "capa", "complaint"]),
        "event_timestamp": _ts(rng),
        "event_category": rng.choice(["instrument_related", "medication", "fall", "process"]),
        "event_severity": rng.choice(["serious", "moderate", "minor", "near_miss"]),
        "instrument_reference": f"INST-{rng.randint(1000, 9999)}" if rng.random() > 0.4 else None,
        "tray_reference": f"TRAY-{rng.randint(100, 999)}" if rng.random() > 0.6 else None,
        "de_identified": True,
        "capa_id": f"CAPA-{rng.randint(1000, 9999)}" if rng.random() > 0.7 else None,
        "rca_status": rng.choice(["open", "closed", None]),
        "facility_id": facility_id or "main",
    }


class SafeCareConnector(BaseConnector):
    """SafeCare connector — adverse events, near misses, good catches."""

    SYSTEM_NAME = "safecare"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = [_qs_record(rng, self.SYSTEM_NAME, self.facility_id) for _ in range(min(limit, 4))]
        return {"records": records, "total_available": rng.randint(30, 200), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(15, 80), "failed": 0, "errors": []}


class RLDatixConnector(BaseConnector):
    """RLDatix connector — incidents, near misses, CAPAs, complaints."""

    SYSTEM_NAME = "rldatix"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = [_qs_record(rng, self.SYSTEM_NAME, self.facility_id) for _ in range(min(limit, 5))]
        return {"records": records, "total_available": rng.randint(50, 300), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(20, 120), "failed": 0, "errors": []}


class MIDASConnector(BaseConnector):
    """MIDAS connector — quality events, sentinel events, RCA records."""

    SYSTEM_NAME = "midas"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = [_qs_record(rng, self.SYSTEM_NAME, self.facility_id) for _ in range(min(limit, 4))]
        return {"records": records, "total_available": rng.randint(20, 150), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(10, 60), "failed": 0, "errors": []}


class VergeHealthConnector(BaseConnector):
    """Verge Health connector — event reports, vendor concerns."""

    SYSTEM_NAME = "verge"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = [_qs_record(rng, self.SYSTEM_NAME, self.facility_id) for _ in range(min(limit, 3))]
        return {"records": records, "total_available": rng.randint(10, 100), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(5, 40), "failed": 0, "errors": []}
