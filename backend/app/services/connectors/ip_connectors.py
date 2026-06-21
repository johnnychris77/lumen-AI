"""P17 Infection Prevention connector stubs."""
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


def _ip_record(rng: random.Random, system: str, facility_id: str) -> dict:
    """Build a de-identified infection prevention event record — no PHI fields."""
    return {
        "source_system": system,
        "source_record_id": f"{system.upper()}-{rng.randint(10000, 99999)}",
        "source_event_type": rng.choice(["hai_alert", "ssi_flag", "outbreak_signal", "review_candidate"]),
        "event_timestamp": _ts(rng),
        "pathogen": rng.choice(["MRSA", "C. diff", "VRE", "Pseudomonas", "Klebsiella", None]),
        "procedure_type": rng.choice(["orthopedic", "cardiac", "general_surgery", "laparoscopic", None]),
        "service_line": rng.choice(["OR", "ICU", "endoscopy", "SPD", None]),
        "instrument_reference": f"INST-{rng.randint(1000, 9999)}" if rng.random() > 0.5 else None,
        "de_identified": True,
        "facility_id": facility_id or "main",
    }


class ICNetConnector(BaseConnector):
    """ICNet connector — HAI surveillance, outbreak signals, infection flags."""

    SYSTEM_NAME = "icnet"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = [_ip_record(rng, self.SYSTEM_NAME, self.facility_id) for _ in range(min(limit, 4))]
        return {"records": records, "total_available": rng.randint(20, 150), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(10, 60), "failed": 0, "errors": []}


class VigiLanzConnector(BaseConnector):
    """VigiLanz connector — HAI alerts, SSI surveillance, pathogen signals."""

    SYSTEM_NAME = "vigilanz"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = [_ip_record(rng, self.SYSTEM_NAME, self.facility_id) for _ in range(min(limit, 4))]
        return {"records": records, "total_available": rng.randint(15, 120), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(8, 50), "failed": 0, "errors": []}


class TheradocConnector(BaseConnector):
    """Theradoc connector — infection prevention alerts, pharmacy surveillance integration."""

    SYSTEM_NAME = "theradoc"

    def test_connection(self) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "test")
        return {"success": True, "message": "Demo connection OK", "latency_ms": rng.randint(20, 150)}

    def preview_import(self, limit: int = 10) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "preview")
        records = [_ip_record(rng, self.SYSTEM_NAME, self.facility_id) for _ in range(min(limit, 3))]
        return {"records": records, "total_available": rng.randint(10, 80), "sample_only": True}

    def run_import(self, since_timestamp=None) -> dict:
        rng = _seed(self.tenant_id + self.SYSTEM_NAME + "run")
        return {"imported": rng.randint(5, 35), "failed": 0, "errors": []}
