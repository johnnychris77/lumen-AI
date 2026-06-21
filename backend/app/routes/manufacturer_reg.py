"""P14: Manufacturer portal onboarding routes."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth

router = APIRouter(prefix="/api/manufacturers", tags=["manufacturer-onboarding"])


class ManufacturerRegisterRequest(BaseModel):
    manufacturer_name: str
    contact_email: str
    company_url: str = ""
    instruments_manufactured: list[str] = []


class ApproveRequest(BaseModel):
    notes: str = ""


@router.post("/register")
def register_manufacturer(
    body: ManufacturerRegisterRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Self-service manufacturer registration — no auth required."""
    from app.models.manufacturer_reg import ManufacturerRegistration
    reg = ManufacturerRegistration(
        manufacturer_name=body.manufacturer_name,
        contact_email=body.contact_email,
        company_url=body.company_url,
        instruments_manufactured=json.dumps(body.instruments_manufactured),
        registration_status="pending",
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return {
        "registration_id": reg.id,
        "manufacturer_name": reg.manufacturer_name,
        "registration_status": reg.registration_status,
        "registered_at": reg.registered_at.isoformat(),
    }


@router.get("/register/{registration_id}")
def check_registration_status(
    registration_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Check registration status — no auth required."""
    from app.models.manufacturer_reg import ManufacturerRegistration
    reg = db.get(ManufacturerRegistration, registration_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found.")
    return {
        "registration_id": reg.id,
        "manufacturer_name": reg.manufacturer_name,
        "registration_status": reg.registration_status,
        "registered_at": reg.registered_at.isoformat(),
        "approved_at": reg.approved_at.isoformat() if reg.approved_at else None,
        "approval_notes": reg.approval_notes,
    }


@router.get("/registrations")
def list_registrations(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """List all registrations — requires auth."""
    require_enterprise_auth(request)
    from app.models.manufacturer_reg import ManufacturerRegistration
    regs = db.query(ManufacturerRegistration).all()
    return {
        "total": len(regs),
        "registrations": [
            {
                "id": r.id,
                "manufacturer_name": r.manufacturer_name,
                "contact_email": r.contact_email,
                "registration_status": r.registration_status,
                "registered_at": r.registered_at.isoformat(),
            }
            for r in regs
        ],
    }


@router.post("/registrations/{registration_id}/approve")
def approve_registration(
    registration_id: int,
    body: ApproveRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Approve a manufacturer registration — requires auth."""
    require_enterprise_auth(request)
    from app.models.manufacturer_reg import ManufacturerRegistration
    reg = db.get(ManufacturerRegistration, registration_id)
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found.")
    reg.registration_status = "approved"
    reg.approved_at = datetime.now(timezone.utc)
    reg.approval_notes = body.notes
    db.commit()
    db.refresh(reg)
    return {
        "registration_id": reg.id,
        "registration_status": reg.registration_status,
        "approved_at": reg.approved_at.isoformat(),
    }
