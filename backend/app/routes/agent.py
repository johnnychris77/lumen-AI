from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models
from app.agent.spd_agent import build_agent_assessment

router = APIRouter(tags=["agent"])


@router.get("/agent/inspection/{inspection_id}")
def get_agent_assessment(inspection_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Inspection not found")

    return build_agent_assessment(row)


@router.get("/agent/feed")
def get_agent_feed(limit: int = 20, db: Session = Depends(get_db)):
    rows = (
        db.query(models.Inspection)
        .order_by(models.Inspection.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [build_agent_assessment(r) for r in rows]
    }
