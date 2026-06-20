"""P14: Pilot conversion service."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.pilot import PilotStatus


def start_pilot(
    db: Session,
    tenant_id: str,
    facility_id: str,
    agreed_kpis: dict,
) -> PilotStatus:
    """Create a new PilotStatus row (90-day pilot)."""
    now = datetime.now(timezone.utc)
    pilot = PilotStatus(
        tenant_id=tenant_id,
        facility_id=facility_id,
        pilot_start_date=now,
        pilot_end_date=now + timedelta(days=90),
        agreed_kpis=json.dumps(agreed_kpis),
        current_kpis=json.dumps({}),
        conversion_ready=False,
    )
    db.add(pilot)
    db.commit()
    db.refresh(pilot)
    return pilot


def get_pilot_status(
    db: Session,
    tenant_id: str,
    facility_id: str,
) -> dict | None:
    """Return pilot status with days_remaining, kpi_progress, conversion_ready."""
    pilot = (
        db.query(PilotStatus)
        .filter(
            PilotStatus.tenant_id == tenant_id,
            PilotStatus.facility_id == facility_id,
        )
        .order_by(PilotStatus.id.desc())
        .first()
    )
    if pilot is None:
        return None

    now = datetime.now(timezone.utc)
    end = pilot.pilot_end_date
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    days_remaining = max(0, (end - now).days)
    agreed = pilot.get_agreed_kpis()
    current = pilot.get_current_kpis()

    kpi_progress: dict = {}
    met_count = 0
    for key, target in agreed.items():
        actual = current.get(key, 0)
        met = actual >= target if isinstance(target, (int, float)) else actual == target
        kpi_progress[key] = {"target": target, "actual": actual, "met": met}
        if met:
            met_count += 1

    conversion_ready = days_remaining <= 15 and met_count >= 4

    return {
        "pilot_id": pilot.id,
        "tenant_id": pilot.tenant_id,
        "facility_id": pilot.facility_id,
        "pilot_start_date": pilot.pilot_start_date.isoformat(),
        "pilot_end_date": end.isoformat(),
        "days_remaining": days_remaining,
        "agreed_kpis": agreed,
        "current_kpis": current,
        "kpi_progress": kpi_progress,
        "kpis_met": met_count,
        "conversion_ready": conversion_ready,
        "converted_at": pilot.converted_at.isoformat() if pilot.converted_at else None,
    }


def convert_pilot(
    db: Session,
    tenant_id: str,
    facility_id: str,
) -> PilotStatus | None:
    """Mark pilot as converted."""
    pilot = (
        db.query(PilotStatus)
        .filter(
            PilotStatus.tenant_id == tenant_id,
            PilotStatus.facility_id == facility_id,
        )
        .order_by(PilotStatus.id.desc())
        .first()
    )
    if pilot is None:
        return None

    pilot.conversion_ready = True
    pilot.converted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pilot)
    return pilot
