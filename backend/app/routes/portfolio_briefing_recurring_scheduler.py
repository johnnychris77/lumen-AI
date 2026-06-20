from __future__ import annotations

from fastapi import APIRouter, Request

from app.auth import get_current_user
from app.portfolio_briefing_recurring_scheduler import (
    run_due_portfolio_briefing_schedules,
    scheduler_status,
    start_recurring_portfolio_briefing_scheduler,
)


router = APIRouter(
    prefix="/portfolio-briefing-scheduler",
    tags=["portfolio-briefing-scheduler"],
)


@router.get("/status")
def get_scheduler_status(
    request: Request,
):
    get_current_user(request)
    return scheduler_status()


@router.post("/start")
def start_scheduler(
    request: Request,
):
    get_current_user(request)
    return start_recurring_portfolio_briefing_scheduler()


@router.post("/run-due")
def run_due_now(
    request: Request,
):
    get_current_user(request)
    return run_due_portfolio_briefing_schedules()
