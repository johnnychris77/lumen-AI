from __future__ import annotations

from io import BytesIO
import json
import zipfile

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.deps import get_db
from app.db import models
from app.retention import compute_retention_metadata
from app.metering import record_usage_event, check_quota
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["trust-center-exports"])


@router.get("/trust-center/attestations.json")
def trust_center_attestations_json(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    quota_state = check_quota(db, tenant_id=tenant["tenant_id"], tenant_name=tenant["tenant_name"], metric_key="trust_center_exported")
    if not quota_state["allowed"]:
        return JSONResponse({"detail": f'Quota exceeded for trust_center_exported. Used {quota_state["used"]} of {quota_state["limit"]}.'}, status_code=429)
    record_usage_event(db, tenant_id=tenant["tenant_id"], tenant_name=tenant["tenant_name"], event_type="trust_center_exported", quantity=1, notes="trust center export")
    payload = {
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "attestations": [
            {
                "control": "Dual-control governance approvals",
                "status": "active",
                "description": "High-risk governance changes require request and separate approval.",
            },
            {
                "control": "Tenant-scoped audit logging",
                "status": "active",
                "description": "Administrative and governance actions are recorded per tenant.",
            },
            {
                "control": "Signed evidence manifests",
                "status": "active",
                "description": "Evidence packs support tamper-evident verification metadata.",
            },
            {
                "control": "Retention and legal hold governance",
                "status": "active",
                "description": "Artifacts can be governed by retention policies and legal hold protections.",
            },
        ],
        "retention": {
            "evidence_pack": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "evidence_pack"),
            "inspection": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "inspection"),
            "audit_log": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "audit_log"),
            "digest_delivery": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "digest_delivery"),
        },
    }
    return JSONResponse(payload)


@router.get("/trust-center/attestations.bundle.zip")
def trust_center_attestations_bundle(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    payload = {
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        "attestations": [
            {
                "control": "Dual-control governance approvals",
                "status": "active",
                "description": "High-risk governance changes require request and separate approval.",
            },
            {
                "control": "Tenant-scoped audit logging",
                "status": "active",
                "description": "Administrative and governance actions are recorded per tenant.",
            },
            {
                "control": "Signed evidence manifests",
                "status": "active",
                "description": "Evidence packs support tamper-evident verification metadata.",
            },
            {
                "control": "Retention and legal hold governance",
                "status": "active",
                "description": "Artifacts can be governed by retention policies and legal hold protections.",
            },
        ],
        "retention": {
            "evidence_pack": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "evidence_pack"),
            "inspection": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "inspection"),
            "audit_log": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "audit_log"),
            "digest_delivery": compute_retention_metadata(db, tenant["tenant_id"], tenant["tenant_name"], "digest_delivery"),
        },
    }

    bio = BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"lumenai_{tenant['tenant_id']}_trust_center_attestations.json", json.dumps(payload, indent=2))
    bio.seek(0)

    return StreamingResponse(
        bio,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=lumenai_{tenant['tenant_id']}_trust_center_attestations.zip"},
    )
