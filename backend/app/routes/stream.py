from fastapi import APIRouter, UploadFile, File, Depends, Form
from sqlalchemy.orm import Session
import os

from app.deps import get_db
from app.db import models
from redis import Redis
from rq import Queue
from app.jobs.inspection_job import run_inspection

router = APIRouter(tags=["stream"])

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


@router.post("/stream/frame")
async def process_frame(
    frame: UploadFile = File(...),
    vendor_name: str = Form(default="unknown"),
    db: Session = Depends(get_db),
):
    image_bytes = await frame.read()
    if not image_bytes:
        raise ValueError("Empty frame uploaded")

    inspection = models.Inspection(
        file_name=frame.filename or "live-frame",
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

    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    redis = Redis.from_url(REDIS_URL)
    q = Queue("lumenai", connection=redis)
    q.enqueue(run_inspection, inspection.id, image_bytes)

    return {
        "status": "queued",
        "inspection": {
            "id": inspection.id,
            "created_at": inspection.created_at.isoformat() if inspection.created_at else None,
            "file_name": inspection.file_name,
            "vendor_name": inspection.vendor_name,
            "status": inspection.status,
        },
    }
