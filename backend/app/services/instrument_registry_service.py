"""P15: National SPD Intelligence Network — instrument registry service."""
from __future__ import annotations

import hashlib
import random
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.instrument_registry import RegistryInstrument

MIN_CONTRIBUTING = 5  # suppress if fewer than 5 facilities contributed


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def lookup_instrument(
    db: Session,
    udi: str | None = None,
    barcode: str | None = None,
) -> dict[str, Any] | None:
    """Find by UDI or barcode."""
    if udi:
        rec = db.query(RegistryInstrument).filter(RegistryInstrument.udi == udi).first()
    elif barcode:
        rec = db.query(RegistryInstrument).filter(RegistryInstrument.barcode == barcode).first()
    else:
        return None

    if rec:
        return _instrument_to_dict(rec)

    # Seeded mock fallback
    key = udi or barcode or "unknown"
    rng = _seed(f"instrument:{key}")
    contrib = rng.randint(3, 25)
    return {
        "udi": udi,
        "barcode": barcode,
        "manufacturer_name": f"Manufacturer-{rng.randint(1, 20)}",
        "model_name": f"Model-{rng.randint(100, 999)}",
        "instrument_category": rng.choice(["endoscope", "surgical_tray", "laparoscopic"]),
        "sterilization_method": rng.choice(["steam", "EtO", "hydrogen_peroxide"]),
        "network_inspection_count": rng.randint(10, 500),
        "network_defect_rate": round(rng.uniform(0.01, 0.15), 4) if contrib >= MIN_CONTRIBUTING else None,
        "network_pass_rate": round(rng.uniform(0.85, 0.99), 4) if contrib >= MIN_CONTRIBUTING else None,
        "contributing_facilities": contrib,
        "registry_status": "active",
        "data_source": "mock",
    }


def register_instrument(db: Session, instrument_data: dict[str, Any]) -> dict[str, Any]:
    """Add instrument to registry."""
    rec = RegistryInstrument(
        udi=instrument_data.get("udi"),
        barcode=instrument_data.get("barcode"),
        qr_code=instrument_data.get("qr_code"),
        keydot_id=instrument_data.get("keydot_id"),
        manufacturer_name=instrument_data.get("manufacturer_name", "Unknown"),
        model_name=instrument_data.get("model_name", "Unknown"),
        instrument_category=instrument_data.get("instrument_category", "general"),
        sterilization_method=instrument_data.get("sterilization_method"),
        ifu_reference=instrument_data.get("ifu_reference"),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _instrument_to_dict(rec)


def update_network_stats(db: Session, udi: str, pass_result: bool) -> dict[str, Any]:
    """Increment network stats counters (anonymized)."""
    rec = db.query(RegistryInstrument).filter(RegistryInstrument.udi == udi).first()
    if not rec:
        return {"status": "not_found", "udi": udi}

    rec.network_inspection_count = (rec.network_inspection_count or 0) + 1
    total = rec.network_inspection_count
    current_pass = (rec.network_pass_rate or 1.0) * (total - 1)
    rec.network_pass_rate = round((current_pass + (1 if pass_result else 0)) / total, 4)
    rec.network_defect_rate = round(1.0 - rec.network_pass_rate, 4)
    rec.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "updated", "udi": udi}


def get_defect_history(db: Session, udi: str) -> dict[str, Any]:
    """Return aggregated defect history — no facility IDs."""
    rec = db.query(RegistryInstrument).filter(RegistryInstrument.udi == udi).first()
    if rec:
        contrib = rec.contributing_facilities or 0
        return {
            "udi": udi,
            "network_inspection_count": rec.network_inspection_count,
            "network_defect_rate": rec.network_defect_rate if contrib >= MIN_CONTRIBUTING else None,
            "network_pass_rate": rec.network_pass_rate if contrib >= MIN_CONTRIBUTING else None,
            "contributing_facilities": contrib,
            "suppressed": contrib < MIN_CONTRIBUTING,
            "note": "No facility identifiers included per anonymization policy",
        }

    # Mock
    rng = _seed(f"defect_history:{udi}")
    contrib = rng.randint(2, 30)
    return {
        "udi": udi,
        "network_inspection_count": rng.randint(20, 1000),
        "network_defect_rate": round(rng.uniform(0.01, 0.20), 4) if contrib >= MIN_CONTRIBUTING else None,
        "network_pass_rate": round(rng.uniform(0.80, 0.99), 4) if contrib >= MIN_CONTRIBUTING else None,
        "contributing_facilities": contrib,
        "suppressed": contrib < MIN_CONTRIBUTING,
        "note": "No facility identifiers included per anonymization policy",
        "data_source": "mock",
    }


def search_registry(
    db: Session,
    query: str,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Search by name/manufacturer."""
    q = db.query(RegistryInstrument)
    if query:
        q = q.filter(
            (RegistryInstrument.manufacturer_name.ilike(f"%{query}%"))
            | (RegistryInstrument.model_name.ilike(f"%{query}%"))
        )
    if category:
        q = q.filter(RegistryInstrument.instrument_category == category)

    results = q.limit(50).all()
    if results:
        return [_instrument_to_dict(r) for r in results]

    # Seeded mock
    rng = _seed(f"search:{query}:{category}")
    count = rng.randint(3, 12)
    categories = ["endoscope", "surgical_tray", "laparoscopic", "sterilization_pouch"]
    return [
        {
            "udi": f"UDI-{rng.randint(10000, 99999)}",
            "manufacturer_name": f"Manufacturer-{rng.randint(1, 20)}",
            "model_name": f"Model-{rng.randint(100, 999)}",
            "instrument_category": rng.choice(categories),
            "registry_status": "active",
            "data_source": "mock",
        }
        for _ in range(count)
    ]


def get_registry_stats(db: Session) -> dict[str, Any]:
    """Return registry size and coverage stats."""
    total = db.query(RegistryInstrument).count()
    active = db.query(RegistryInstrument).filter(RegistryInstrument.registry_status == "active").count()
    recalled = db.query(RegistryInstrument).filter(RegistryInstrument.registry_status == "recalled").count()
    return {
        "total_instruments": total or 2847,
        "active": active or 2731,
        "recalled": recalled or 43,
        "discontinued": max(0, (total or 2847) - (active or 2731) - (recalled or 43)),
        "data_source": "real" if total > 0 else "mock",
    }


def _instrument_to_dict(rec: RegistryInstrument) -> dict[str, Any]:
    contrib = rec.contributing_facilities or 0
    return {
        "id": rec.id,
        "udi": rec.udi,
        "barcode": rec.barcode,
        "manufacturer_name": rec.manufacturer_name,
        "model_name": rec.model_name,
        "instrument_category": rec.instrument_category,
        "sterilization_method": rec.sterilization_method,
        "ifu_reference": rec.ifu_reference,
        "network_inspection_count": rec.network_inspection_count,
        "network_defect_rate": rec.network_defect_rate if contrib >= MIN_CONTRIBUTING else None,
        "network_pass_rate": rec.network_pass_rate if contrib >= MIN_CONTRIBUTING else None,
        "contributing_facilities": contrib,
        "registry_status": rec.registry_status,
        "data_source": "real",
    }
