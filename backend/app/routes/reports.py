from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.report_delivery import deliver_report
from app.reporting import record_report_run, run_report
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["reports"])


class SavedReportPayload(BaseModel):
    name: str
    report_type: str
    filters: dict = {}
    schedule_cron: str = ""
    delivery_channel: str = ""
    delivery_target: str = ""
    is_enabled: bool = True
    notes: str = ""


def _row(row: models.SavedReport) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "name": row.name,
        "report_type": row.report_type,
        "filter_json": row.filter_json,
        "schedule_cron": row.schedule_cron,
        "delivery_channel": row.delivery_channel,
        "delivery_target": row.delivery_target,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _run_row(row: models.ReportRun) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "report_id": row.report_id,
        "report_type": row.report_type,
        "status": row.status,
        "filter_json": row.filter_json,
        "result_json": row.result_json,
        "delivery_status": row.delivery_status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/reports")
def list_reports(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.SavedReport)
        .filter(models.SavedReport.tenant_id == tenant["tenant_id"])
        .order_by(models.SavedReport.id.desc())
        .all()
    )
    return {"items": [_row(r) for r in rows]}


@router.post("/reports")
def create_report(
    payload: SavedReportPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.SavedReport(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        name=payload.name,
        report_type=payload.report_type,
        filter_json=json.dumps(payload.filters)[:4000],
        schedule_cron=payload.schedule_cron,
        delivery_channel=payload.delivery_channel,
        delivery_target=payload.delivery_target,
        is_enabled=payload.is_enabled,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="saved_report_create",
        resource_type="saved_report",
        resource_id=row.id,
        request=request,
        details=_row(row),
        compliance_flag=True,
    )

    return {"item": _row(row)}


@router.get("/reports/{report_id}/preview")
def preview_report(
    report_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = (
        db.query(models.SavedReport)
        .filter(
            models.SavedReport.id == report_id,
            models.SavedReport.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Saved report not found")

    filters = json.loads(row.filter_json or "{}")
    result = run_report(db, tenant["tenant_id"], tenant["tenant_name"], row.report_type, filters)
    return {"report": _row(row), "preview": result}


@router.post("/reports/{report_id}/run")
def run_saved_report(
    report_id: int,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = (
        db.query(models.SavedReport)
        .filter(
            models.SavedReport.id == report_id,
            models.SavedReport.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Saved report not found")

    filters = json.loads(row.filter_json or "{}")
    result = run_report(db, tenant["tenant_id"], tenant["tenant_name"], row.report_type, filters)

    delivery = {"sent": False, "reason": "No delivery requested"}
    delivery_status = "not_sent"
    if row.delivery_channel:
        delivery = deliver_report(row.delivery_channel, row.delivery_target, {
            "tenant_id": tenant["tenant_id"],
            "tenant_name": tenant["tenant_name"],
            "report_type": row.report_type,
            "result": result,
        })
        delivery_status = "sent" if delivery.get("sent") else "failed"

    run = record_report_run(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        report_id=row.id,
        report_type=row.report_type,
        filters=filters,
        result=result,
        status="completed",
        delivery_status=delivery_status,
    )

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="saved_report_run",
        resource_type="report_run",
        resource_id=run.id,
        request=request,
        details={"report": _row(row), "result": result, "delivery": delivery},
        compliance_flag=True,
    )

    return {"run": _run_row(run), "result": result, "delivery": delivery}


@router.get("/reports/history")
def report_history(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.ReportRun)
        .filter(models.ReportRun.tenant_id == tenant["tenant_id"])
        .order_by(models.ReportRun.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_run_row(r) for r in rows]}


@router.post("/reports/{report_id}/schedule")
def schedule_report(
    report_id: int,
    payload: SavedReportPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = (
        db.query(models.SavedReport)
        .filter(
            models.SavedReport.id == report_id,
            models.SavedReport.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Saved report not found")

    row.schedule_cron = payload.schedule_cron
    row.delivery_channel = payload.delivery_channel
    row.delivery_target = payload.delivery_target
    row.is_enabled = payload.is_enabled
    row.notes = payload.notes or row.notes
    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="saved_report_schedule_update",
        resource_type="saved_report",
        resource_id=row.id,
        request=request,
        details=_row(row),
        compliance_flag=True,
    )

    return {"item": _row(row)}
