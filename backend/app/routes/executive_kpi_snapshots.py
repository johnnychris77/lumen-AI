from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.executive_kpi_scheduler import generate_executive_kpi_trend_narrative
from app.executive_kpi_snapshots import (
    capture_executive_kpi_snapshot,
    executive_kpi_trends,
    get_latest_executive_kpi_snapshot,
    list_executive_kpi_snapshots,
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


router = APIRouter(prefix="/executive-kpi-snapshots", tags=["executive-kpi-snapshots"])


class ExecutiveKpiSnapshotCapturePayload(BaseModel):
    snapshot_label: str = Field(default="Executive Operating Metrics Snapshot")


@router.post("/capture")
def capture_snapshot(
    request: Request,
    payload: ExecutiveKpiSnapshotCapturePayload,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return capture_executive_kpi_snapshot(db, snapshot_label=payload.snapshot_label)


@router.get("")
def list_snapshots(
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return list_executive_kpi_snapshots(db)


@router.get("/latest")
def latest_snapshot(
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return get_latest_executive_kpi_snapshot(db) or {}


@router.get("/trends")
def trends(
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return executive_kpi_trends(db)


@router.get("/narrative")
def narrative(
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return generate_executive_kpi_trend_narrative(db)
