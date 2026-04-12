from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.leadership_packet_exports import build_leadership_packet
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["leadership-packets"])


class LeadershipPacketPayload(BaseModel):
    briefing_id: int


def _row(row: models.LeadershipPacket) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "briefing_id": row.briefing_id,
        "packet_type": row.packet_type,
        "title": row.title,
        "docx_path": row.docx_path,
        "pptx_path": row.pptx_path,
        "pdf_path": row.pdf_path,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _packet_or_404(db: Session, tenant_id: str, packet_id: int) -> models.LeadershipPacket:
    row = (
        db.query(models.LeadershipPacket)
        .filter(
            models.LeadershipPacket.id == packet_id,
            models.LeadershipPacket.tenant_id == tenant_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Leadership packet not found")
    return row


@router.post("/leadership-packets/generate")
def generate_leadership_packet(
    payload: LeadershipPacketPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = build_leadership_packet(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        briefing_id=payload.briefing_id,
    )

    result = _row(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="leadership_packet_generate",
        resource_type="leadership_packet",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )

    return result


@router.get("/leadership-packets")
def list_leadership_packets(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.LeadershipPacket)
        .filter(models.LeadershipPacket.tenant_id == tenant["tenant_id"])
        .order_by(models.LeadershipPacket.id.desc())
        .limit(100)
        .all()
    )
    return {"items": [_row(r) for r in rows]}


@router.get("/leadership-packets/{packet_id}")
def get_leadership_packet(
    packet_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = _packet_or_404(db, tenant["tenant_id"], packet_id)
    return _row(row)


@router.get("/leadership-packets/{packet_id}/docx")
def download_leadership_packet_docx(
    packet_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = _packet_or_404(db, tenant["tenant_id"], packet_id)
    path = Path(row.docx_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="DOCX file not found")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=path.name)


@router.get("/leadership-packets/{packet_id}/pptx")
def download_leadership_packet_pptx(
    packet_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = _packet_or_404(db, tenant["tenant_id"], packet_id)
    path = Path(row.pptx_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PPTX file not found")
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation", filename=path.name)


@router.get("/leadership-packets/{packet_id}/pdf")
def download_leadership_packet_pdf(
    packet_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = _packet_or_404(db, tenant["tenant_id"], packet_id)
    path = Path(row.pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    return FileResponse(path, media_type="application/pdf", filename=path.name)
