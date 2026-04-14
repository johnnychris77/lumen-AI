from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.packet_release_governance import (
    approve_packet_release,
    reject_packet_release,
    request_packet_release,
)
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["packet-releases"])


class PacketReleaseRequestPayload(BaseModel):
    packet_id: int
    attestation_required: bool = True
    attestation_text: str = ""


class PacketReleaseDecisionPayload(BaseModel):
    approval_notes: str = ""


def _release_row(row: models.PacketRelease) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "packet_id": row.packet_id,
        "packet_title": row.packet_title,
        "audience_type": row.audience_type,
        "requested_by": row.requested_by,
        "requested_role": row.requested_role,
        "status": row.status,
        "approver_email": row.approver_email,
        "approver_role": row.approver_role,
        "approval_notes": row.approval_notes,
        "attestation_required": row.attestation_required,
        "attestation_text": row.attestation_text,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
    }


def _history_row(row: models.PacketReleaseHistory) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "release_id": row.release_id,
        "packet_id": row.packet_id,
        "action_type": row.action_type,
        "actor_email": row.actor_email,
        "actor_role": row.actor_role,
        "details_json": row.details_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/packet-releases/request")
def request_release(
    payload: PacketReleaseRequestPayload,
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

    row = request_packet_release(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        packet_id=packet.id,
        packet_title=packet.title,
        audience_type=packet.packet_type,
        requested_by=current_user["user_email"],
        requested_role=current_user["role_name"],
        attestation_required=payload.attestation_required,
        attestation_text=payload.attestation_text,
    )

    result = _release_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="packet_release_requested",
        resource_type="packet_release",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.post("/packet-releases/{release_id}/approve")
def approve_release(
    release_id: int,
    payload: PacketReleaseDecisionPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    try:
        row = approve_packet_release(
            db,
            release_id=release_id,
            tenant_id=tenant["tenant_id"],
            approver_email=current_user["user_email"],
            approver_role=current_user["role_name"],
            approval_notes=payload.approval_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = _release_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="packet_release_approved",
        resource_type="packet_release",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.post("/packet-releases/{release_id}/reject")
def reject_release(
    release_id: int,
    payload: PacketReleaseDecisionPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    try:
        row = reject_packet_release(
            db,
            release_id=release_id,
            tenant_id=tenant["tenant_id"],
            approver_email=current_user["user_email"],
            approver_role=current_user["role_name"],
            approval_notes=payload.approval_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    result = _release_row(row)
    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="packet_release_rejected",
        resource_type="packet_release",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return {"item": result}


@router.get("/packet-releases")
def list_releases(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.PacketRelease)
        .filter(models.PacketRelease.tenant_id == tenant["tenant_id"])
        .order_by(models.PacketRelease.id.desc())
        .all()
    )
    return {"items": [_release_row(r) for r in rows]}


@router.get("/packet-releases/{release_id}")
def get_release(
    release_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = (
        db.query(models.PacketRelease)
        .filter(
            models.PacketRelease.id == release_id,
            models.PacketRelease.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Packet release not found")
    return _release_row(row)


@router.get("/packet-releases/history")
def release_history(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.PacketReleaseHistory)
        .filter(models.PacketReleaseHistory.tenant_id == tenant["tenant_id"])
        .order_by(models.PacketReleaseHistory.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_history_row(r) for r in rows]}
