from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models

router = APIRouter(tags=["inspections"])


@router.get("/inspections/{inspection_id}")
def get_inspection(inspection_id: int, db: Session = Depends(get_db)):
    row = db.query(models.Inspection).filter(models.Inspection.id == inspection_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Inspection not found")

    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "file_name": row.file_name,
        "stain_detected": row.stain_detected,
        "confidence": row.confidence,
        "material_type": row.material_type,
        "status": row.status,
        "model_name": getattr(row, "model_name", "lumenai-baseline"),
        "model_version": getattr(row, "model_version", "0.1.0"),
        "inference_timestamp": row.inference_timestamp.isoformat() if getattr(row, "inference_timestamp", None) else None,
    }
