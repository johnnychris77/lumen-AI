from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.deps import get_db
from app.db import models

router = APIRouter(tags=["analytics"])

@router.get("/analytics/powerbi")
def powerbi_dataset(db: Session = Depends(get_db)):

    rows = db.query(models.Inspection).all()

    dataset = []

    for r in rows:
        dataset.append({
            "inspection_id": r.id,
            "instrument_type": r.instrument_type,
            "detected_issue": r.detected_issue,
            "material_type": r.material_type,
            "confidence": r.confidence,
            "status": r.status,
            "timestamp": r.created_at
        })

    return dataset
