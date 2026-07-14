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
    *,
    organization: str = "",
    department: str = "",
    clinical_lead: str = "",
    technical_lead: str = "",
    quality_lead: str = "",
    validation_coordinator: str = "",
    pilot_end_date: datetime | None = None,
    pilot_sponsor: str = "",
    product_owner: str = "",
    engineering_lead: str = "",
    success_criteria: str = "",
    pilot_duration_days: int | None = None,
) -> PilotStatus:
    """Create a new PilotStatus row (90-day pilot by default).

    Shadow (Phase 6) §2 adds the optional organization/department/lead
    fields and an explicit end date; Advisor (Phase 7) §2 adds the
    remaining governance roles and success criteria. Existing callers that
    omit them keep the original 90-day, blank-lead behavior unchanged.
    """
    now = datetime.now(timezone.utc)
    pilot = PilotStatus(
        tenant_id=tenant_id,
        facility_id=facility_id,
        pilot_start_date=now,
        pilot_end_date=pilot_end_date or (now + timedelta(days=90)),
        agreed_kpis=json.dumps(agreed_kpis),
        current_kpis=json.dumps({}),
        conversion_ready=False,
        organization=organization,
        department=department,
        clinical_lead=clinical_lead,
        technical_lead=technical_lead,
        quality_lead=quality_lead,
        validation_coordinator=validation_coordinator,
        pilot_sponsor=pilot_sponsor,
        product_owner=product_owner,
        engineering_lead=engineering_lead,
        success_criteria=success_criteria,
        pilot_duration_days=pilot_duration_days,
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
