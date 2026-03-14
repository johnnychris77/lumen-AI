from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from io import StringIO
import csv

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
    limit: int = Query(default=20, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.Inspection)
        .order_by(models.Inspection.id.desc())
        .limit(limit)
        .all()
    )
    return {"items": [inspection_response(r) for r in rows]}


@router.get("/history/summary")
async def get_history_summary(db: Session = Depends(get_db)):
    rows = db.query(models.Inspection).all()

    total = len(rows)
    completed = sum(1 for r in rows if (r.status or "").lower() == "completed")
    queued = sum(1 for r in rows if (r.status or "").lower() == "queued")
    running = sum(1 for r in rows if (r.status or "").lower() == "running")
    failed = sum(1 for r in rows if (r.status or "").lower() == "failed")

    issue_counts = {}
    instrument_counts = {}

    for r in rows:
        issue = (r.detected_issue or "unknown").strip() or "unknown"
        instrument = (r.instrument_type or "unknown").strip() or "unknown"

        issue_counts[issue] = issue_counts.get(issue, 0) + 1
        instrument_counts[instrument] = instrument_counts.get(instrument, 0) + 1

    top_issues = sorted(
        [{"label": k, "count": v} for k, v in issue_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    top_instruments = sorted(
        [{"label": k, "count": v} for k, v in instrument_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:5]

    return {
        "total_inspections": total,
        "completed": completed,
        "queued": queued,
        "running": running,
        "failed": failed,
        "top_issues": top_issues,
        "top_instruments": top_instruments,
    }


@router.get("/history/export.json")
async def export_history_json(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Inspection)
        .order_by(models.Inspection.id.desc())
        .all()
    )
    return JSONResponse({"items": [inspection_response(r) for r in rows]})


@router.get("/history/export.csv")
async def export_history_csv(db: Session = Depends(get_db)):
    rows = (
        db.query(models.Inspection)
        .order_by(models.Inspection.id.desc())
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id",
        "created_at",
        "file_name",
        "status",
        "stain_detected",
        "confidence",
        "material_type",
        "instrument_type",
        "detected_issue",
        "inference_mode",
        "model_name",
        "model_version",
        "inference_timestamp",
    ])

    for r in rows:
        writer.writerow([
            r.id,
            r.created_at.isoformat() if r.created_at else "",
            r.file_name,
            r.status,
            r.stain_detected,
            r.confidence,
            r.material_type,
            r.instrument_type,
            r.detected_issue,
            r.inference_mode,
            r.model_name,
            r.model_version,
            r.inference_timestamp.isoformat() if r.inference_timestamp else "",
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lumenai_history_export.csv"},
    )
