"""v3.0 — Project Sentinel, Section 5: Digital Twin Monitoring.

Tiers each physical instrument's Digital Twin into Monitor/Critical/
Escalation using real signals from `instrument_condition_service.
instrument_condition_history` — condition trend, repair count, corrosion
history — rather than the still-mock `QualityTwinState`/`QualityForecast`
scores. An instrument with insufficient history is never flagged; "no
signal" is reported honestly, not defaulted to Monitor.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.sentinel_orchestration import TWIN_TIER_CRITICAL, TWIN_TIER_ESCALATION, TWIN_TIER_MONITOR, DigitalTwinFlag
from app.services.instrument_condition_service import instrument_condition_history
from app.services.pre_sterilization_command_center_service import _instrument_identity

_RECENT_WINDOW_DAYS = 180


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _tier_for(history: dict) -> tuple[str, str] | None:
    trend = history["condition_trend"]
    repair_count = history["repair_count"]
    corrosion_count = history["corrosion_history_count"]

    if trend == "declining" and repair_count >= 2:
        return TWIN_TIER_ESCALATION, (
            f"Condition trend is declining with {repair_count} prior repair/remove-from-service events."
        )
    if trend == "declining" or repair_count >= 1 or corrosion_count >= 2:
        return TWIN_TIER_CRITICAL, (
            f"Condition trend: {trend}; repair history: {repair_count}; corrosion history: {corrosion_count}."
        )
    if history["inspection_count"] >= 2:
        return TWIN_TIER_MONITOR, f"Stable/improving trend with {history['inspection_count']} inspections on record — routine monitoring."
    return None


def _upsert_flag(db: Session, tenant_id: str, *, instrument_identity: str, instrument_type: str, tier: str, reason: str) -> DigitalTwinFlag:
    existing = (
        db.query(DigitalTwinFlag)
        .filter(
            DigitalTwinFlag.tenant_id == tenant_id, DigitalTwinFlag.instrument_identity == instrument_identity,
            DigitalTwinFlag.resolved_at.is_(None),
        )
        .first()
    )
    if existing is not None:
        existing.tier = tier
        existing.reason = reason
        return existing
    row = DigitalTwinFlag(tenant_id=tenant_id, instrument_identity=instrument_identity, instrument_type=instrument_type, tier=tier, reason=reason)
    db.add(row)
    return row


def monitor_digital_twins(db: Session, tenant_id: str) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=_RECENT_WINDOW_DAYS)
    recent_inspections = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.created_at >= since)
        .all()
    )
    identities = sorted({_instrument_identity(i) for i in recent_inspections if not _instrument_identity(i).startswith("untracked:")})

    touched: list[DigitalTwinFlag] = []
    for identity in identities:
        history = instrument_condition_history(db, tenant_id, identity)
        if history is None:
            continue
        tiering = _tier_for(history)
        if tiering is None:
            continue
        tier, reason = tiering
        touched.append(_upsert_flag(db, tenant_id, instrument_identity=identity, instrument_type=history["instrument_type"], tier=tier, reason=reason))

    db.commit()
    for row in touched:
        db.refresh(row)

    return list_open_flags(db, tenant_id)


def list_open_flags(db: Session, tenant_id: str, *, tier: str = "") -> list[dict]:
    q = db.query(DigitalTwinFlag).filter(DigitalTwinFlag.tenant_id == tenant_id, DigitalTwinFlag.resolved_at.is_(None))
    if tier:
        q = q.filter(DigitalTwinFlag.tier == tier)
    rows = q.order_by(DigitalTwinFlag.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def resolve_flag(db: Session, tenant_id: str, flag_id: int) -> dict | None:
    row = db.query(DigitalTwinFlag).filter(DigitalTwinFlag.id == flag_id, DigitalTwinFlag.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
