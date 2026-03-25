from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from io import StringIO, BytesIO
import csv
import json
import zipfile
import os

from openpyxl import Workbook

from app.deps import get_db
from app.db import models
from app.notifications.notifier import dispatch_alert
from app.authz import require_roles

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


def alert_event_response(row: models.AlertEvent) -> dict:
    return {
        "id": row.id,
        "inspection_id": row.inspection_id,
        "vendor_name": row.vendor_name,
        "instrument_type": row.instrument_type,
        "detected_issue": row.detected_issue,
        "risk_score": row.risk_score,
        "channel": row.channel,
        "sent": row.sent,
        "status_code": row.status_code,
        "failure_reason": row.failure_reason,
        "dispatch_batch_id": row.dispatch_batch_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def fetch_alert_events(db: Session, limit: int | None = None):
    q = db.query(models.AlertEvent).order_by(models.AlertEvent.id.desc())
    if limit:
        q = q.limit(limit)
    return q.all()


@router.get("/alerts/channel-health")
def alerts_channel_health(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    channels = ["slack", "teams", "email"]
    items = []

    for channel in channels:
        last_event = (
            db.query(models.AlertEvent)
            .filter(models.AlertEvent.channel == channel)
            .order_by(models.AlertEvent.id.desc())
            .first()
        )

        last_success = (
            db.query(models.AlertEvent)
            .filter(models.AlertEvent.channel == channel, models.AlertEvent.sent == True)
            .order_by(models.AlertEvent.id.desc())
            .first()
        )

        items.append({
            "channel": channel,
            "last_attempt_at": last_event.created_at.isoformat() if last_event and last_event.created_at else None,
            "last_attempt_sent": bool(last_event.sent) if last_event else False,
            "last_status_code": last_event.status_code if last_event else "",
            "last_failure_reason": last_event.failure_reason if last_event else "",
            "last_dispatch_batch_id": last_event.dispatch_batch_id if last_event else "",
            "last_success_at": last_success.created_at.isoformat() if last_success and last_success.created_at else None,
        })

    return {"items": items}


def alert_events_csv_text(rows):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "inspection_id",
        "vendor_name",
        "instrument_type",
        "detected_issue",
        "risk_score",
        "channel",
        "sent",
        "status_code",
        "failure_reason",
        "dispatch_batch_id",
        "created_at",
    ])
    for r in rows:
        writer.writerow([
            r.id,
            r.inspection_id,
            r.vendor_name,
            r.instrument_type,
            r.detected_issue,
            r.risk_score,
            r.channel,
            r.sent,
            r.status_code,
            r.failure_reason,
            r.dispatch_batch_id,
            r.created_at.isoformat() if r.created_at else "",
        ])
    return output.getvalue()


def alert_events_xlsx_bytes(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Alert Audit Trail"
    ws.append([
        "id",
        "inspection_id",
        "vendor_name",
        "instrument_type",
        "detected_issue",
        "risk_score",
        "channel",
        "sent",
        "status_code",
        "failure_reason",
        "dispatch_batch_id",
        "created_at",
    ])

    for r in rows:
        ws.append([
            r.id,
            r.inspection_id,
            r.vendor_name,
            r.instrument_type,
            r.detected_issue,
            r.risk_score,
            r.channel,
            r.sent,
            r.status_code,
            r.failure_reason,
            r.dispatch_batch_id,
            r.created_at.isoformat() if r.created_at else "",
        ])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.getvalue()


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
def alerts_status(current_user=Depends(require_roles("admin", "spd_manager"))):
    slack_configured = bool(os.getenv("LUMENAI_SLACK_WEBHOOK_URL", "").strip())
    teams_configured = bool(os.getenv("LUMENAI_TEAMS_WEBHOOK_URL", "").strip())
    email_configured = bool(
        os.getenv("LUMENAI_SMTP_HOST", "").strip()
        and os.getenv("LUMENAI_ALERT_EMAIL_TO", "").strip()
    )

    return {
        "enabled": _truthy(os.getenv("LUMENAI_ALERTS_ENABLED", "false")),
        "channels": {
            "slack": {"configured": slack_configured, "enabled": slack_configured},
            "teams": {"configured": teams_configured, "enabled": teams_configured},
            "email": {"configured": email_configured, "enabled": email_configured},
        },
    }


@router.post("/alerts/send/{inspection_id}")
def send_alert_for_inspection(inspection_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles("admin", "spd_manager"))):
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


@router.post("/alerts/resend/{alert_event_id}")
def resend_from_audit_event(alert_event_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles("admin", "spd_manager"))):
    event = (
        db.query(models.AlertEvent)
        .filter(models.AlertEvent.id == alert_event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")

    inspection = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == event.inspection_id)
        .first()
    )
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    alert = alert_response(inspection)
    result = dispatch_alert(alert)
    return {
        "source_alert_event_id": alert_event_id,
        "inspection_id": inspection.id,
        "alert": alert,
        "dispatch": result,
    }


@router.get("/alerts/history")
def alerts_history(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    rows = fetch_alert_events(db, limit=limit)
    return {"items": [alert_event_response(r) for r in rows]}


@router.get("/alerts/history/export.json")
def alerts_history_export_json(db: Session = Depends(get_db), current_user=Depends(require_roles("admin", "spd_manager"))):
    rows = fetch_alert_events(db)
    return JSONResponse({"items": [alert_event_response(r) for r in rows]})


@router.get("/alerts/history/export.csv")
def alerts_history_export_csv(db: Session = Depends(get_db), current_user=Depends(require_roles("admin", "spd_manager"))):
    rows = fetch_alert_events(db)
    text = alert_events_csv_text(rows)
    return StreamingResponse(
        iter([text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lumenai_alert_audit_trail.csv"},
    )


@router.get("/alerts/history/export.xlsx")
def alerts_history_export_xlsx(db: Session = Depends(get_db), current_user=Depends(require_roles("admin", "spd_manager"))):
    rows = fetch_alert_events(db)
    content = alert_events_xlsx_bytes(rows)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=lumenai_alert_audit_trail.xlsx"},
    )


@router.get("/alerts/history/export.bundle.zip")
def alerts_history_export_bundle(db: Session = Depends(get_db), current_user=Depends(require_roles("admin", "spd_manager"))):
    rows = fetch_alert_events(db)
    json_content = json.dumps({"items": [alert_event_response(r) for r in rows]}, indent=2)
    csv_content = alert_events_csv_text(rows)
    xlsx_content = alert_events_xlsx_bytes(rows)

    bio = BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lumenai_alert_audit_trail.json", json_content)
        zf.writestr("lumenai_alert_audit_trail.csv", csv_content)
        zf.writestr("lumenai_alert_audit_trail.xlsx", xlsx_content)

    bio.seek(0)
    return StreamingResponse(
        bio,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=lumenai_alert_audit_trail_bundle.zip"},
    )
