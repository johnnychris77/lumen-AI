from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.audit import log_audit_event
from app.db import SessionLocal
from app.governance_sla_scanner import (
    run_scanner_once,
    scanner_recommendations,
    scanner_status,
)
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["governance-sla-scanner"])


@router.get("/governance-sla-scanner/status")
def get_scanner_status(
    tenant: dict = Depends(resolve_tenant),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return {
        "tenant_id": tenant["tenant_id"],
        "tenant_name": tenant["tenant_name"],
        **scanner_status(),
    }


@router.post("/governance-sla-scanner/run")
def run_scanner(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    result = run_scanner_once()

    db = SessionLocal()
    try:
        log_audit_event(
            db,
            tenant_id=tenant["tenant_id"],
            tenant_name=tenant["tenant_name"],
            actor_email=current_user["user_email"],
            actor_role=current_user["role_name"],
            action_type="governance_sla_scanner_run",
            resource_type="governance_sla_scanner",
            request=request,
            details=result,
            compliance_flag=True,
        )
    finally:
        db.close()

    return result


@router.get("/governance-sla-scanner/recommendations")
def get_recommendations(
    tenant: dict = Depends(resolve_tenant),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return scanner_recommendations(tenant["tenant_id"], tenant["tenant_name"])
