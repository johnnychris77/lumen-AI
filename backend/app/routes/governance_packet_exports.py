from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.governance_packet_exports import (
    create_governance_packet_record,
    deliver_governance_packet,
    export_governance_packet,
    get_governance_packet,
    get_governance_packet_export,
    list_governance_packet_deliveries,
    list_governance_packet_exports,
    list_governance_packets,
)


def get_db():
    if hasattr(db_session, "get_db"):
        yield from db_session.get_db()
        return

    if hasattr(db_session, "get_session"):
        yield from db_session.get_session()
        return

    if hasattr(db_session, "SessionLocal"):
        db = db_session.SessionLocal()
        try:
            yield db
        finally:
            db.close()
        return

    raise RuntimeError("No database session provider found in app.db.session")


router = APIRouter(prefix="/governance-packets", tags=["governance-packets"])


class GovernancePacketCreatePayload(BaseModel):
    packet_title: str | None = None


class GovernancePacketDeliveryPayload(BaseModel):
    export_id: int | None = None
    delivery_channel: Literal["internal", "email", "webhook"] = "internal"
    delivery_target: str = Field(default="executive-governance-council")
    message: str = Field(default="Executive governance packet is ready for review.")


@router.post("")
def create_packet(
    payload: GovernancePacketCreatePayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return create_governance_packet_record(db, packet_title=payload.packet_title)


@router.get("")
def list_packets(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_governance_packets(db)


@router.get("/{packet_id}")
def get_packet(
    packet_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    packet = get_governance_packet(db, packet_id)
    if not packet:
        raise HTTPException(status_code=404, detail="Governance packet not found")
    return packet


@router.post("/{packet_id}/exports")
def create_packet_export(
    packet_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    try:
        return export_governance_packet(db, packet_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{packet_id}/exports")
def list_packet_exports(
    packet_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_governance_packet_exports(db, packet_id)


@router.post("/{packet_id}/deliver")
def deliver_packet(
    packet_id: int,
    payload: GovernancePacketDeliveryPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    try:
        return deliver_governance_packet(
            db=db,
            packet_id=packet_id,
            export_id=payload.export_id,
            delivery_channel=payload.delivery_channel,
            delivery_target=payload.delivery_target,
            message=payload.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{packet_id}/deliveries")
def list_packet_deliveries(
    packet_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_governance_packet_deliveries(db, packet_id)


@router.get("/exports/{export_id}/{artifact_type}")
def download_packet_artifact(
    export_id: int,
    artifact_type: Literal["docx", "pptx", "pdf"],
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    export = get_governance_packet_export(db, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Governance packet export not found")

    path = Path(export.get(f"{artifact_type}_path") or "")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{artifact_type.upper()} artifact not found")

    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
    }

    return FileResponse(
        path,
        media_type=media_types[artifact_type],
        filename=path.name,
    )
