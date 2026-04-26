from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.portfolio_briefing_schedules import (
    create_portfolio_briefing_schedule,
    get_portfolio_briefing_schedule,
    list_portfolio_briefing_schedules,
    run_portfolio_briefing_schedule_now,
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


router = APIRouter(prefix="/portfolio-briefing-schedules", tags=["portfolio-briefing-schedules"])


class PortfolioBriefingScheduleCreatePayload(BaseModel):
    schedule_name: str = Field(default="Monthly Executive Portfolio Board Package")
    briefing_type: str = Field(default="board_portfolio")
    audience: str = Field(default="board")
    period_label: str = Field(default="Scheduled Portfolio Board Review")
    delivery_channel: Literal["email", "webhook", "internal"] = "internal"
    delivery_target: str = Field(default="executive-board")
    message: str = Field(default="Portfolio board briefing package is ready for review.")
    is_enabled: bool = True


@router.post("")
def create_schedule(
    payload: PortfolioBriefingScheduleCreatePayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return create_portfolio_briefing_schedule(
        db=db,
        schedule_name=payload.schedule_name,
        briefing_type=payload.briefing_type,
        audience=payload.audience,
        period_label=payload.period_label,
        delivery_channel=payload.delivery_channel,
        delivery_target=payload.delivery_target,
        message=payload.message,
        is_enabled=payload.is_enabled,
    )


@router.get("")
def list_schedules(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_portfolio_briefing_schedules(db)


@router.get("/{schedule_id}")
def get_schedule(
    schedule_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    schedule = get_portfolio_briefing_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Portfolio briefing schedule not found")
    return schedule


@router.post("/{schedule_id}/run-now")
def run_schedule_now(
    schedule_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    try:
        return run_portfolio_briefing_schedule_now(db, schedule_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
