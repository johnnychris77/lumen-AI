from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models

router = APIRouter(tags=["history"])


def inspection_response(row: models.Inspection) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "file_name": row.file_name,
        "stain_detected": row.stain_detected,
        "confidence": row.confidence,
        "material_type": row.material_type,
        "status": row.status,
        "model_name": row.model_name,
        "model_version": row.model_version,
        "inference_timestamp": row.inference_timestamp.isoformat() if row.inference_timestamp else None,
        "instrument_type": row.instrument_type,
        "detected_issue": row.detected_issue,
        "inference_mode": row.inference_mode,
    }


@router.get("/history")
async def get_history(
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.Inspection)
        .order_by(models.Inspection.id.desc())
        .limit(limit)
        .all()
    )
    return {"items": [inspection_response(r) for r in rows]}
