from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.executive_kpi_scheduler import (
    executive_kpi_scheduler_status,
    generate_executive_kpi_trend_narrative,
    run_kpi_snapshot_now,
    start_executive_kpi_scheduler,
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


router = APIRouter(prefix="/executive-kpi-scheduler", tags=["executive-kpi-scheduler"])


@router.get("/status")
def scheduler_status(
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    get_current_user(authorization)
    return executive_kpi_scheduler_status()


@router.post("/start")
def start_scheduler(
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    get_current_user(authorization)
    return start_executive_kpi_scheduler()


@router.post("/run-now")
def run_now(
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    get_current_user(authorization)
    return run_kpi_snapshot_now()


@router.get("/narrative")
def trend_narrative(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return generate_executive_kpi_trend_narrative(db)
