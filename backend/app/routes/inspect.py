from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
import os

from app.deps import get_db
from app.db import models

from redis import Redis
from rq import Queue

from app.jobs.inspection_job import run_inspection

router = APIRouter(tags=["inspect"])

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


@router.post("/inspect")
async def inspect_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    contents = await file.read()
    if not contents:
        raise ValueError("Empty file uploaded")

    row = models.Inspection(
        file_name=file.filename or "uploaded-image",
        stain_detected=False,
        confidence=0.0,
        material_type="unknown",
        status="queued",
        model_name="lumenai-baseline",
        model_version="0.1.0",
        inference_timestamp=None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    redis = Redis.from_url(REDIS_URL)
    q = Queue("lumenai", connection=redis)
    q.enqueue(run_inspection, row.id, contents)

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
    }
