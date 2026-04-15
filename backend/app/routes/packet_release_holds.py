from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.packet_release_governance import (
    log_release_history,
    release_governance_status,
)
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["packet-release-holds"])


class ReleaseHoldPayload(BaseModel):
    packet_id: int
    hold_type: str = "compliance"
    reason: str


class ClearHoldPayload(BaseModel):
    cleared_notes: str = ""


class EmergencyOverridePayload(BaseModel):
    packet_id: int
    justification: str
    override_type: str = "emergency_release"


def _hold_row(row: models.PacketReleaseHold) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "packet_id": row.packet_id,
        "hold_type": row.hold_type,
        "reason": row.reason,
        "placed_by": row.placed_by,
        "placed_role": row.placed_role,
        "is_active": row.is_active,
        "cleared_by": row.cleared_by,
        "cleared_role": row.cleared_role,
        "cleared_notes": row.cleared_notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "cleared_at": row.cleared_at.isoformat() if row.cleared_at else None,
    }


def _override_row(row: models.PacketReleaseOverride) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "packet_id": row.packet_id,
        "override_type": row.override_type,
        "justification": row.justification,
        "approved_by": row.approved_by,
        "approved_role": row.approved_role,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/packet-release-holds")
def create_hold(
    payload: ReleaseHoldPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    packet = (
        db.query(models.LeadershipPacket)
        .filter(
            models.LeadershipPacket.id == payload.packet_id,
            models.LeadershipPacket.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not packet:
        raise HTTPException(status_code=404, detail="Leadership packet not found")

    row = models.PacketReleaseHold(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        packet_id=payload.packet_id,
        hold_type=payload.hold_type,
        reason=payload.reason,
        placed_by=current_user["user_email"],
        placed_role=current_user["role_name"],
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_release_history(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        release_id=0,
        packet_id=payload.packet_id,
        action_type="hold_created",
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        details=_hold_row(row),
    )

    result = _hold_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="packet_release_hold_create",
        resource_type="packet_release_hold",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.get("/packet-release-holds")
def list_holds(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.PacketReleaseHold)
        .filter(models.PacketReleaseHold.tenant_id == tenant["tenant_id"])
        .order_by(models.PacketReleaseHold.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_hold_row(r) for r in rows]}


@router.post("/packet-release-holds/{hold_id}/clear")
def clear_hold(
    hold_id: int,
    payload: ClearHoldPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = (
        db.query(models.PacketReleaseHold)
        .filter(
            models.PacketReleaseHold.id == hold_id,
            models.PacketReleaseHold.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Packet release hold not found")

    row.is_active = False
    row.cleared_by = current_user["user_email"]
    row.cleared_role = current_user["role_name"]
    row.cleared_notes = payload.cleared_notes
    row.cleared_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)

    log_release_history(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        release_id=0,
        packet_id=row.packet_id,
        action_type="hold_cleared",
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        details=_hold_row(row),
    )

    result = _hold_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="packet_release_hold_clear",
        resource_type="packet_release_hold",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.post("/packet-release-overrides/emergency")
def emergency_override(
    payload: EmergencyOverridePayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    packet = (
        db.query(models.LeadershipPacket)
        .filter(
            models.LeadershipPacket.id == payload.packet_id,
            models.LeadershipPacket.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not packet:
        raise HTTPException(status_code=404, detail="Leadership packet not found")

    row = models.PacketReleaseOverride(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        packet_id=payload.packet_id,
        override_type=payload.override_type,
        justification=payload.justification,
        approved_by=current_user["user_email"],
        approved_role=current_user["role_name"],
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_release_history(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        release_id=0,
        packet_id=payload.packet_id,
        action_type="emergency_override_created",
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        details=_override_row(row),
    )

    result = _override_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="packet_release_emergency_override",
        resource_type="packet_release_override",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.get("/packet-release-overrides")
def list_overrides(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.PacketReleaseOverride)
        .filter(models.PacketReleaseOverride.tenant_id == tenant["tenant_id"])
        .order_by(models.PacketReleaseOverride.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_override_row(r) for r in rows]}


@router.get("/packet-release-governance/status/{packet_id}")
def get_release_governance_status(
    packet_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return release_governance_status(db, tenant["tenant_id"], packet_id)
