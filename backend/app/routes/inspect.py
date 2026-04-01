from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models
from app.jobs.inspection_job import run_inspection
from app.tenant import resolve_tenant

router = APIRouter(tags=["inspect"])


def inspection_response(row: models.Inspection) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "file_name": row.file_name,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "vendor_name": row.vendor_name,
        "site_name": row.site_name,
        "status": row.status,
    }


@router.post("/stream/frame")
async def stream_frame(
    frame: UploadFile = File(...),
    vendor_name: str = Form("unknown"),
    site_name: str = Form("default-site"),
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
):
    file_bytes = await frame.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty frame uploaded")

    row = models.Inspection(
        file_name=frame.filename or "frame.bin",
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        vendor_name=vendor_name,
        site_name=site_name,
        status="queued",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    run_inspection(row.id, file_bytes)

    return {
        "status": "queued",
        "inspection": inspection_response(row),
    }
