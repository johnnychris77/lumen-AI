from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.release_governance_dashboard import (
    dashboard_summary,
    exceptions,
    packet_status,
    readiness,
)
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["release-governance-dashboard"])


@router.get("/release-governance/dashboard")
def release_dashboard(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return dashboard_summary(db, tenant["tenant_id"], tenant["tenant_name"])


@router.get("/release-governance/readiness")
def release_readiness(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return readiness(db, tenant["tenant_id"])


@router.get("/release-governance/exceptions")
def release_exceptions(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return exceptions(db, tenant["tenant_id"])


@router.get("/release-governance/packets/{packet_id}/status")
def release_packet_status(
    packet_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return packet_status(db, tenant["tenant_id"], packet_id)
