from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.session import get_db
from app.portfolio_briefing_exports import (
    build_portfolio_briefing_export,
    distribute_portfolio_briefing,
    get_portfolio_briefing_export,
    list_portfolio_briefing_deliveries,
    list_portfolio_briefing_exports,
)


router = APIRouter(prefix="/portfolio-briefings", tags=["portfolio-briefing-exports"])


class PortfolioBriefingDistributePayload(BaseModel):
    export_id: int | None = None
    delivery_channel: Literal["email", "webhook", "internal"] = "internal"
    delivery_target: str = Field(default="executive-board")
    message: str = Field(default="Portfolio briefing package is ready for executive review.")


@router.post("/{briefing_id}/exports")
def create_portfolio_briefing_export(
    briefing_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    try:
        return build_portfolio_briefing_export(db, briefing_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{briefing_id}/exports")
def list_exports_for_briefing(
    briefing_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_portfolio_briefing_exports(db, briefing_id)


@router.get("/exports/{export_id}")
def get_export_record(
    export_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    export = get_portfolio_briefing_export(db, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Portfolio briefing export not found")
    return export


@router.get("/exports/{export_id}/{artifact_type}")
def download_export_artifact(
    export_id: int,
    artifact_type: Literal["docx", "pptx", "pdf"],
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    export = get_portfolio_briefing_export(db, export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Portfolio briefing export not found")

    path_key = f"{artifact_type}_path"
    artifact_path = Path(export.get(path_key) or "")

    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail=f"{artifact_type.upper()} artifact not found")

    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "pdf": "application/pdf",
    }

    return FileResponse(
        artifact_path,
        media_type=media_types[artifact_type],
        filename=artifact_path.name,
    )


@router.post("/{briefing_id}/distribute")
def distribute_briefing(
    briefing_id: int,
    payload: PortfolioBriefingDistributePayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return distribute_portfolio_briefing(
        db=db,
        briefing_id=briefing_id,
        export_id=payload.export_id,
        delivery_channel=payload.delivery_channel,
        delivery_target=payload.delivery_target,
        message=payload.message,
    )


@router.get("/{briefing_id}/deliveries")
def list_deliveries_for_briefing(
    briefing_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_portfolio_briefing_deliveries(db, briefing_id)
