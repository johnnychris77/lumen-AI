from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import os

from app.deps import get_db
from app.db import models
from app.notifications.notifier import dispatch_alert

router = APIRouter(tags=["alerts"])


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def alert_response(r: models.Inspection) -> dict:
    return {
        "inspection_id": r.id,
        "file_name": r.file_name,
        "vendor_name": r.vendor_name,
        "instrument_type": r.instrument_type,
        "detected_issue": r.detected_issue,
        "risk_score": int(r.risk_score or 0),
        "status": r.status,
        "message": f"Inspection {r.id} flagged for SPD review: {r.detected_issue} on {r.instrument_type}.",
    }


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
            items.append(alert_response(r))

    return {"items": items}


@router.get("/alerts/status")
def alerts_status():
    slack_configured = bool(os.getenv("LUMENAI_SLACK_WEBHOOK_URL", "").strip())
    teams_configured = bool(os.getenv("LUMENAI_TEAMS_WEBHOOK_URL", "").strip())
    email_configured = bool(
        os.getenv("LUMENAI_SMTP_HOST", "").strip()
        and os.getenv("LUMENAI_ALERT_EMAIL_TO", "").strip()
    )

    return {
        "enabled": _truthy(os.getenv("LUMENAI_ALERTS_ENABLED", "false")),
        "channels": {
            "slack": {
                "configured": slack_configured,
                "enabled": slack_configured,
            },
            "teams": {
                "configured": teams_configured,
                "enabled": teams_configured,
            },
            "email": {
                "configured": email_configured,
                "enabled": email_configured,
            },
        },
    }


@router.post("/alerts/send/{inspection_id}")
def send_alert_for_inspection(inspection_id: int, db: Session = Depends(get_db)):
    row = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Inspection not found")

    alert = alert_response(row)
    result = dispatch_alert(alert)
    return {
        "inspection_id": inspection_id,
        "alert": alert,
        "dispatch": result,
    }
