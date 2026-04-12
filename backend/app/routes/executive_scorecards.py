from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.executive_reporting import build_board_narrative, build_scorecard_summary, persist_scorecard
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["executive-scorecards"])


class ScorecardPayload(BaseModel):
    scorecard_type: str = "monthly"
    days: int = 30
    period_label: str = ""


def _row(row: models.ExecutiveScorecard) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "scorecard_type": row.scorecard_type,
        "period_label": row.period_label,
        "summary_json": row.summary_json,
        "narrative_text": row.narrative_text,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/executive-scorecards")
def list_scorecards(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.ExecutiveScorecard)
        .filter(models.ExecutiveScorecard.tenant_id == tenant["tenant_id"])
        .order_by(models.ExecutiveScorecard.id.desc())
        .limit(100)
        .all()
    )
    return {"items": [_row(r) for r in rows]}


@router.post("/executive-scorecards/generate")
def generate_scorecard(
    payload: ScorecardPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    period_label = payload.period_label or f"last_{payload.days}_days"
    summary = build_scorecard_summary(db, tenant["tenant_id"], tenant["tenant_name"], payload.days)
    narrative = build_board_narrative(summary)
    row = persist_scorecard(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        scorecard_type=payload.scorecard_type,
        period_label=period_label,
        summary=summary,
        narrative_text=narrative,
    )

    result = {
        "scorecard": _row(row),
        "summary": summary,
        "narrative": narrative,
    }

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="executive_scorecard_generate",
        resource_type="executive_scorecard",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )

    return result


@router.get("/executive-scorecards/latest")
def latest_scorecard(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = (
        db.query(models.ExecutiveScorecard)
        .filter(models.ExecutiveScorecard.tenant_id == tenant["tenant_id"])
        .order_by(models.ExecutiveScorecard.id.desc())
        .first()
    )
    if not row:
        return JSONResponse({"detail": "No executive scorecards found."}, status_code=404)

    return {
        "scorecard": _row(row),
        "summary": json.loads(row.summary_json or "{}"),
        "narrative": row.narrative_text,
    }
