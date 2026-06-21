"""P14: Pilot conversion gate routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.services.pilot_service import convert_pilot, get_pilot_status, start_pilot

router = APIRouter(prefix="/api/pilot", tags=["pilot"])


class StartPilotRequest(BaseModel):
    facility_id: str = ""
    agreed_kpis: dict = {}


@router.post("/start")
def pilot_start(
    body: StartPilotRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    pilot = start_pilot(db, tenant_id, body.facility_id, body.agreed_kpis)
    return {
        "pilot_id": pilot.id,
        "tenant_id": pilot.tenant_id,
        "facility_id": pilot.facility_id,
        "pilot_start_date": pilot.pilot_start_date.isoformat(),
        "pilot_end_date": pilot.pilot_end_date.isoformat(),
        "status": "started",
    }


@router.get("/status")
def pilot_status(
    request: Request,
    facility_id: str = "",
    db: Session = Depends(get_db),
) -> dict:
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    status = get_pilot_status(db, tenant_id, facility_id)
    if status is None:
        raise HTTPException(status_code=404, detail="No active pilot found.")
    return status


@router.post("/convert")
def pilot_convert(
    request: Request,
    facility_id: str = "",
    db: Session = Depends(get_db),
) -> dict:
    auth = require_enterprise_auth(request)
    tenant_id = auth.tenant_id
    pilot = convert_pilot(db, tenant_id, facility_id)
    if pilot is None:
        raise HTTPException(status_code=404, detail="No active pilot found.")
    return {
        "pilot_id": pilot.id,
        "conversion_ready": pilot.conversion_ready,
        "converted_at": pilot.converted_at.isoformat() if pilot.converted_at else None,
        "status": "converted",
    }
