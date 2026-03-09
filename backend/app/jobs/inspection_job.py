from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db import models
from app.ai.inference import LumenAIModel


def run_inspection(inspection_id: int, file_bytes: bytes) -> None:
    """
    RQ job:
      - mark row running
      - run model prediction
      - persist results
      - mark completed/failed
    """
    db: Session = SessionLocal()
    try:
        row = (
            db.query(models.Inspection)
            .filter(models.Inspection.id == inspection_id)
            .first()
        )
        if not row:
            return

        row.status = "running"
        db.add(row)
        db.commit()

        model = LumenAIModel()
        res = model.predict(file_bytes)

        row.stain_detected = bool(res.get("stain_detected", False))
        row.confidence = float(res.get("confidence", 0.0))
        row.material_type = str(res.get("material_type", "unknown"))
        row.model_name = str(res.get("model_name", "lumenai-baseline"))
        row.model_version = str(res.get("model_version", "0.1.0"))

        ts = res.get("inference_timestamp")
        if ts:
            try:
                row.inference_timestamp = datetime.fromisoformat(ts)
            except Exception:
                row.inference_timestamp = None

        row.status = "completed"

        db.add(row)
        db.commit()

    except Exception:
        try:
            row = (
                db.query(models.Inspection)
                .filter(models.Inspection.id == inspection_id)
                .first()
            )
            if row:
                row.status = "failed"
                db.add(row)
                db.commit()
        finally:
            raise
    finally:
        db.close()
