from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.core.baseline_ranking_contract import (
    BASELINE_RANKING_INPUT_FIELDS,
    apply_baseline_ranking_to_inspection_payload_if_present,
    build_baseline_ranking_audit_evidence,
)
from app.deps import get_db
from app.db import models
from app.jobs.inspection_job import run_inspection
from app.metering import record_usage_event, check_quota
from app.event_dispatcher import dispatch_event
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
@router.post("/baseline-ranking/audit-evidence")
def baseline_ranking_audit_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    return build_baseline_ranking_audit_evidence(payload)

@router.post("/stream/frame")
async def stream_frame(
    frame: UploadFile = File(...),
    vendor_name: str = Form("unknown"),
    site_name: str = Form("default-site"),
    capture_method: str | None = Form(None),
    barcode_value: str | None = Form(None),
    qr_code_value: str | None = Form(None),
    keydot_value: str | None = Form(None),
    catalog_number: str | None = Form(None),
    model_number: str | None = Form(None),
    manufacturer: str | None = Form(None),
    vendor: str | None = Form(None),
    instrument_name: str | None = Form(None),
    instrument_category: str | None = Form(None),
    instrument_match_status: str | None = Form(None),
    baseline_status: str | None = Form(None),
    baseline_source: str | None = Form(None),
    baseline_confidence: str | None = Form(None),
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "vendor_user")),
):
    file_bytes = await frame.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty frame uploaded")

    quota_state = check_quota(db, tenant_id=tenant["tenant_id"], tenant_name=tenant["tenant_name"], metric_key="inspection_submitted")
    if not quota_state["allowed"]:
        raise HTTPException(status_code=429, detail=f'Quota exceeded for inspection_submitted. Used {quota_state["used"]} of {quota_state["limit"]}.')

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

    inspection_payload = apply_baseline_ranking_to_inspection_payload_if_present(
        {
            "capture_method": capture_method,
            "barcode_value": barcode_value,
            "qr_code_value": qr_code_value,
            "keydot_value": keydot_value,
            "catalog_number": catalog_number,
            "model_number": model_number,
            "manufacturer": manufacturer,
            "vendor": vendor,
            "instrument_name": instrument_name,
            "instrument_category": instrument_category,
            "instrument_match_status": instrument_match_status,
            "baseline_status": baseline_status,
            "baseline_source": baseline_source,
            "baseline_confidence": baseline_confidence,
        }
    )

    record_usage_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        event_type="inspection_submitted",
        quantity=1,
        resource_id=row.id,
        notes=row.file_name,
    )

    run_inspection(row.id, file_bytes)

    has_baseline_context = any(
        inspection_payload.get(field) not in (None, "") for field in BASELINE_RANKING_INPUT_FIELDS
    )
    event_payload = {
        "inspection_id": row.id,
        "file_name": row.file_name,
        "vendor_name": row.vendor_name,
        "site_name": row.site_name,
        "status": row.status,
    }
    if has_baseline_context:
        event_payload["baseline_ranking"] = inspection_payload

    dispatch_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        trigger_type="inspection_submitted",
        payload=event_payload,
    )

    response = {
        "status": "queued",
        "inspection": inspection_response(row),
    }
    if has_baseline_context:
        response["baseline_ranking"] = inspection_payload
    return response
from typing import Any
