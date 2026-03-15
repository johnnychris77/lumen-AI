from fastapi import APIRouter, Depends, File, UploadFile, Form
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
    vendor_name: str = Form(default="unknown"),
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
        instrument_type="unknown",
        detected_issue="unknown",
        inference_mode="deterministic-fallback",
        risk_score=0,
        vendor_name=vendor_name or "unknown",
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
        "instrument_type": row.instrument_type,
        "detected_issue": row.detected_issue,
        "inference_mode": row.inference_mode,
        "risk_score": row.risk_score,
        "vendor_name": row.vendor_name,
    }
