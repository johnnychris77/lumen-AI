from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db import models
from app.ai.inference import infer  # adjust if your function is named differently


def run_inspection(inspection_id: int, file_bytes: bytes) -> None:
    """
    RQ job entrypoint: loads Inspection row, updates status, runs inference,
    saves results back to DB.
    """
    db: Session = SessionLocal()
    try:
        row = db.query(models.Inspection).filter(models.Inspection.id == inspection_id).first()
        if not row:
            return

        row.status = "running"
        db.add(row)
        db.commit()

        # ---- model inference ----
        # Expect infer(...) returns dict with stain_detected/confidence/material_type
        res = infer(file_bytes)

        row.stain_detected = bool(res.get("stain_detected", False))
        row.confidence = float(res.get("confidence", 0.0))
        row.material_type = str(res.get("material_type", "unknown"))
        row.status = "completed"

        db.add(row)
        db.commit()

    except Exception:
        # best-effort fail mark
        try:
            row = db.query(models.Inspection).filter(models.Inspection.id == inspection_id).first()
            if row:
                row.status = "failed"
                db.add(row)
                db.commit()
        finally:
            raise
    finally:
        db.close()
