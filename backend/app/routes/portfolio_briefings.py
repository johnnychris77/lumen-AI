from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.audit import log_audit_event
from app.db import models
from app.deps import get_db
from app.portfolio_authz import require_portfolio_access
from app.portfolio_briefings import generate_portfolio_briefing

router = APIRouter(tags=["portfolio-briefings"])


class PortfolioBriefingPayload(BaseModel):
    briefing_type: str = "board_portfolio"
    audience: str = "board"
    period_label: str = ""


def _row(row: models.PortfolioBriefing) -> dict:
    return {
        "id": row.id,
        "briefing_type": row.briefing_type,
        "audience": row.audience,
        "period_label": row.period_label,
        "title": row.title,
        "executive_summary": row.executive_summary,
        "board_narrative": row.board_narrative,
        "summary_json": row.summary_json,
        "top_risks_json": row.top_risks_json,
        "next_steps_json": row.next_steps_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/portfolio-briefings")
def list_portfolio_briefings(
    db: Session = Depends(get_db),
    current_user=Depends(require_portfolio_access),
):
    rows = (
        db.query(models.PortfolioBriefing)
        .order_by(models.PortfolioBriefing.id.desc())
        .limit(100)
        .all()
    )
    return {"items": [_row(r) for r in rows]}


@router.post("/portfolio-briefings/generate")
def generate_portfolio_briefing_route(
    payload: PortfolioBriefingPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_portfolio_access),
):
    row = generate_portfolio_briefing(
        db,
        briefing_type=payload.briefing_type,
        audience=payload.audience,
        period_label=payload.period_label,
    )

    result = _row(row)
    log_audit_event(
        db,
        tenant_id="portfolio",
        tenant_name="Portfolio",
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="portfolio_briefing_generate",
        resource_type="portfolio_briefing",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result


@router.get("/portfolio-briefings/{briefing_id}")
def get_portfolio_briefing(
    briefing_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_portfolio_access),
):
    row = (
        db.query(models.PortfolioBriefing)
        .filter(models.PortfolioBriefing.id == briefing_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Portfolio briefing not found")
    return _row(row)


@router.get("/portfolio-briefings/{briefing_id}/summary")
def get_portfolio_briefing_summary(
    briefing_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_portfolio_access),
):
    row = (
        db.query(models.PortfolioBriefing)
        .filter(models.PortfolioBriefing.id == briefing_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Portfolio briefing not found")
    return {
        "id": row.id,
        "title": row.title,
        "executive_summary": row.executive_summary,
        "summary_json": row.summary_json,
        "top_risks_json": row.top_risks_json,
        "next_steps_json": row.next_steps_json,
    }


@router.get("/portfolio-briefings/{briefing_id}/board-narrative")
def get_portfolio_briefing_board_narrative(
    briefing_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_portfolio_access),
):
    row = (
        db.query(models.PortfolioBriefing)
        .filter(models.PortfolioBriefing.id == briefing_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Portfolio briefing not found")
    return {
        "id": row.id,
        "title": row.title,
        "board_narrative": row.board_narrative,
    }
