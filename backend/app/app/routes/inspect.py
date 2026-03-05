from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
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
    """
    Async inspection:
      - create inspection row as queued
      - enqueue RQ job
      - return queued inspection
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    row = models.Inspection(
        file_name=file.filename or "uploaded-file",
        stain_detected=False,
        confidence=0.0,
        material_type="unknown",
        status="queued",
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
    }
