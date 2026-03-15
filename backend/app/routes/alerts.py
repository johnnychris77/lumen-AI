from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models

router = APIRouter(tags=["alerts"])


@router.get("/alerts/feed")
def alerts_feed(limit: int = 20, db: Session = Depends(get_db)):
    rows = (
        db.query(models.Inspection)
        .order_by(models.Inspection.id.desc())
        .limit(limit)
        .all()
    )

    items = []
    for r in rows:
        risk_score = int(r.risk_score or 0)
        issue = (r.detected_issue or "unknown").lower()
        alert_needed = risk_score >= 50 or issue in {"debris", "stain", "corrosion"}

        if alert_needed:
            items.append({
                "inspection_id": r.id,
                "file_name": r.file_name,
                "vendor_name": r.vendor_name,
                "instrument_type": r.instrument_type,
                "detected_issue": r.detected_issue,
                "risk_score": risk_score,
                "status": r.status,
                "message": f"Inspection {r.id} flagged for SPD review: {r.detected_issue} on {r.instrument_type}.",
            })

    return {"items": items}
