from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

from app.ai.inference import LumenAIModel
from app.ai.inference_gate import (
    MODE_AI_UNAVAILABLE,
    NOT_EVALUATED,
    STATUS_AI_UNAVAILABLE,
    STATUS_FAILED,
)
from app.db import SessionLocal
from app.db import models
from app.reports.pdf_report import generate_report

# Row status for an inspection the AI did not evaluate. It is deliberately not
# "completed": a completed row reads as an evaluated instrument.
ROW_STATUS_AI_UNAVAILABLE = "ai_unavailable"
ROW_STATUS_FAILED = "failed"
ROW_STATUS_SIMULATED = "simulated"

# Mirrors app.services.ai_result_integrity: the persisted signal that no
# verified AI evaluation exists for this row.
AI_ANALYSIS_UNAVAILABLE = "AI_UNAVAILABLE"


def _apply_not_evaluated(row, res: dict) -> None:
    """Persist an explicit not-evaluated state. The legacy columns are NOT
    NULL, so they hold neutral sentinels — never a finding, a confidence or a
    risk — and ``status`` / ``inference_mode`` / ``detected_issue`` say so."""
    row.stain_detected = False
    row.confidence = 0.0
    row.material_type = "unknown"
    row.instrument_type = "unknown"
    row.detected_issue = NOT_EVALUATED
    row.model_name = "none"
    row.model_version = "none"
    row.inference_mode = str(res.get("inference_mode") or MODE_AI_UNAVAILABLE)
    row.risk_score = 0
    row.inference_timestamp = None
    if hasattr(row, "ai_analysis_status"):
        row.ai_analysis_status = AI_ANALYSIS_UNAVAILABLE
    row.status = (
        ROW_STATUS_FAILED if res.get("analysis_status") == STATUS_FAILED else ROW_STATUS_AI_UNAVAILABLE
    )


def run_inspection(inspection_id: int, file_bytes: bytes) -> None:
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

        analysis_status = res.get("analysis_status")
        if analysis_status in (STATUS_AI_UNAVAILABLE, STATUS_FAILED):
            # P4.7.1 (SCI-03): nothing was evaluated. No finding is stored and no
            # report is generated — a report would present the row as inspected.
            _apply_not_evaluated(row, res)
            db.add(row)
            db.commit()
            return

        simulated = bool(res.get("simulated"))

        row.stain_detected = bool(res.get("stain_detected", False))
        row.confidence = float(res.get("confidence", 0.0) or 0.0)
        row.material_type = str(res.get("material_type", "unknown"))
        row.model_name = str(res.get("model_name", "lumenai-baseline"))
        row.model_version = str(res.get("model_version", "0.1.0"))
        row.instrument_type = str(res.get("instrument_type", "unknown"))
        row.detected_issue = str(res.get("detected_issue", "unknown"))
        row.inference_mode = str(res.get("inference_mode", MODE_AI_UNAVAILABLE))
        row.risk_score = int(res.get("risk_score", 0) or 0)

        ts = res.get("inference_timestamp")
        if ts:
            try:
                row.inference_timestamp = datetime.fromisoformat(ts)
            except Exception:
                row.inference_timestamp = None

        if simulated:
            # Dev/test simulation only: visibly not a completed inspection, and
            # never a verified AI result.
            row.status = ROW_STATUS_SIMULATED
            if hasattr(row, "ai_analysis_status"):
                row.ai_analysis_status = AI_ANALYSIS_UNAVAILABLE
            db.add(row)
            db.commit()
            return

        row.status = "completed"

        db.add(row)
        db.commit()
        db.refresh(row)

        generate_report(row)

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
