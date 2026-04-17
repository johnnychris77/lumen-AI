from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.customer_operations_hub import (
    operations_hub_summary,
    run_health_snapshot_action,
    run_renewal_risk_action,
    run_sla_scan_action,
    tenant_status_summary,
    tenant_work_queue,
)
from app.deps import get_db
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["customer-operations-hub"])


@router.get("/customer-operations-hub/summary")
def get_summary(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return operations_hub_summary(db, tenant["tenant_id"], tenant["tenant_name"])


@router.get("/customer-operations-hub/work-queue")
def get_work_queue(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return tenant_work_queue(db, tenant["tenant_id"], tenant["tenant_name"])


@router.get("/customer-operations-hub/status")
def get_status(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return tenant_status_summary(db, tenant["tenant_id"], tenant["tenant_name"])


@router.post("/customer-operations-hub/actions/run-health-snapshot")
def run_health_snapshot(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    result = run_health_snapshot_action(db, tenant["tenant_id"], tenant["tenant_name"])

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="customer_operations_hub_run_health_snapshot",
        resource_type="customer_health_snapshot",
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result


@router.post("/customer-operations-hub/actions/run-renewal-risk")
def run_renewal_risk(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    result = run_renewal_risk_action(db, tenant["tenant_id"], tenant["tenant_name"])

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="customer_operations_hub_run_renewal_risk",
        resource_type="renewal_risk_case",
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result


@router.post("/customer-operations-hub/actions/run-sla-scan")
def run_sla_scan(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    result = run_sla_scan_action()

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="customer_operations_hub_run_sla_scan",
        resource_type="governance_sla_event",
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result
