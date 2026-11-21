from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
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
from app.security.tenant_context import resolve_verified_tenant

router = APIRouter(tags=["inspect"])

# Tenant a platform admin writes to when no tenant is named. Only an explicit
# platform admin can reach this default — every other principal must hold a
# verified membership (see _verified_write_tenant).
_ADMIN_DEFAULT_TENANT = "default-tenant"


def _verified_write_tenant(current_user, requested_tenant_id: str | None) -> dict:
    """P4.7.1 (SEC-R2-03): the tenant an inspection is written to.

    Previously this route used ``app.tenant.resolve_tenant``, which returned
    whatever ``X-Tenant-Id`` header the client sent — any authenticated caller
    could write an inspection row into any tenant. The tenant is now resolved
    by the project's verified resolver:

    * a non-admin is scoped to a tenant they hold an ENABLED, verified
      membership for; a requested tenant outside their memberships is 403;
    * no verified membership at all is 403 (never a default tenant);
    * a platform admin may name a tenant explicitly, else the default tenant.

    The tenant name is derived from the verified id — the client-supplied
    ``X-Tenant-Name`` header is no longer trusted either.
    """
    requested = (requested_tenant_id or "").strip() or None
    scope = resolve_verified_tenant(current_user, requested_tenant_id=requested)
    tenant_id = scope.tenant_id or _ADMIN_DEFAULT_TENANT
    return {"tenant_id": tenant_id, "tenant_name": tenant_id.replace("-", " ").title()}


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
    x_tenant_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "vendor_user")),
):
    # Authorization and verified tenant resolution happen BEFORE the upload is
    # read or any inference runs.
    tenant = _verified_write_tenant(current_user, x_tenant_id)

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
    # The job ran synchronously in its own session: reload so the response and
    # the dispatched event report the REAL outcome (e.g. "ai_unavailable"),
    # not the stale "queued" the row was created with.
    db.refresh(row)

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
        "status": row.status,
        "inspection": inspection_response(row),
        # P4.7.1: explicit AI state. "ai_unavailable" / "failed" mean the image
        # was NOT evaluated — never that the instrument is clean.
        "ai_evaluated": row.status == "completed",
        "inference_mode": row.inference_mode,
        "human_review_required": True,
    }
    if has_baseline_context:
        response["baseline_ranking"] = inspection_payload
    return response
from typing import Any
