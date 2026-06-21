"""P15: National SPD Intelligence Network — recall signal detection engine."""
from __future__ import annotations

import hashlib
import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.recall_signal import RecallSignal

MIN_FACILITIES_SIGNAL = 3  # minimum facilities to surface a recall signal


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def signal_strength_score(
    n_facilities: int,
    recency_days: int,
    finding_count: int,
) -> float:
    """Weighted score 0.0–1.0."""
    facility_weight = min(n_facilities / 20.0, 1.0) * 0.5
    recency_weight = max(0.0, 1.0 - recency_days / 90.0) * 0.3
    count_weight = min(finding_count / 50.0, 1.0) * 0.2
    return round(facility_weight + recency_weight + count_weight, 4)


def detect_recall_signals(db: Session) -> list[dict[str, Any]]:
    """Scan across network participants for recurring patterns; surface when N>=3 and strength>0.3."""
    # DB-first
    existing = db.query(RecallSignal).filter(RecallSignal.status == "active").all()
    if existing:
        return [_signal_to_dict(s) for s in existing]

    # Seeded mock fallback
    mock_patterns = [
        ("endoscope", "contamination_post_reprocessing", 7, 14, 23),
        ("surgical_tray", "packaging_defect", 5, 30, 12),
        ("laparoscopic_instrument", "repeated_failure_tip", 4, 7, 31),
        ("sterilization_pouch", "seal_breach", 8, 3, 45),
        ("robotic_instrument", "residue_detected", 3, 21, 9),
    ]

    results = []
    for category, finding_type, n_fac, recency, count in mock_patterns:
        strength = signal_strength_score(n_fac, recency, count)
        if n_fac < MIN_FACILITIES_SIGNAL or strength <= 0.3:
            continue

        rng = _seed(f"signal:{category}:{finding_type}")
        manuf_hash = hashlib.sha256(f"manufacturer_{rng.randint(1, 10)}".encode()).hexdigest()[:12]

        results.append({
            "signal_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{category}:{finding_type}")),
            "signal_type": "recurring_contamination" if "contamination" in finding_type else "recurring_defect",
            "manufacturer_pseudonym": manuf_hash,
            "instrument_category": category,
            "finding_type": finding_type,
            "n_facilities_reporting": n_fac,
            "first_observed": (datetime.utcnow() - timedelta(days=recency + 30)).isoformat(),
            "last_observed": (datetime.utcnow() - timedelta(days=recency)).isoformat(),
            "signal_strength": strength,
            "status": "active",
            "escalated_to_fda": False,
        })

    return results


def get_active_signals(db: Session) -> list[dict[str, Any]]:
    """Return all active signals (anonymized)."""
    db_signals = db.query(RecallSignal).filter(RecallSignal.status == "active").all()
    if db_signals:
        return [_signal_to_dict(s) for s in db_signals]
    return detect_recall_signals(db)


def get_signals_for_tenant(db: Session, tenant_id: str) -> list[dict[str, Any]]:
    """Return signals relevant to this tenant's instrument types."""
    all_signals = get_active_signals(db)
    # In real implementation, filter by tenant's instrument inventory
    # For mock: return a seeded subset
    rng = _seed(f"tenant_signals:{tenant_id}")
    count = rng.randint(1, max(1, len(all_signals)))
    return all_signals[:count]


def escalate_signal(db: Session, signal_id: str) -> dict[str, Any]:
    """Mark escalated_to_fda=True, set status='escalated'."""
    sig = db.query(RecallSignal).filter(RecallSignal.signal_id == signal_id).first()
    if sig:
        sig.escalated_to_fda = True
        sig.status = "escalated"
        db.commit()
        db.refresh(sig)
        return _signal_to_dict(sig)
    # Mock response for non-DB signal
    return {
        "signal_id": signal_id,
        "status": "escalated",
        "escalated_to_fda": True,
        "message": "Signal escalated to FDA",
    }


def _signal_to_dict(s: RecallSignal) -> dict[str, Any]:
    return {
        "signal_id": s.signal_id,
        "signal_type": s.signal_type,
        "manufacturer_pseudonym": s.manufacturer_pseudonym,
        "instrument_category": s.instrument_category,
        "finding_type": s.finding_type,
        "n_facilities_reporting": s.n_facilities_reporting,
        "first_observed": s.first_observed.isoformat() if s.first_observed else None,
        "last_observed": s.last_observed.isoformat() if s.last_observed else None,
        "signal_strength": s.signal_strength,
        "status": s.status,
        "escalated_to_fda": s.escalated_to_fda,
    }
