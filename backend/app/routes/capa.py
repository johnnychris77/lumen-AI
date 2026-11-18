import csv
import io
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.tenant_scope import authorized_tenant
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.services.capa_service import (
    capa_summary,
    build_capa_powerbi_rows,
    capa_escalation_summary,
    capa_governance_scorecard,
    create_capa,
    create_capa_from_audit_signal,
    list_capas,
    get_capa,
    update_capa,
)


router = APIRouter()

# Tenant isolation (P472-03 AW-11). The role dependency on each route says WHO may
# use the CAPA register; it resolves no tenant. Every handler therefore also
# resolves the caller's membership-verified tenant inline with
#     authorized_tenant(require_enterprise_auth(request, db=db))
# and passes it to the service, which scopes every read and write to it. A CAPA
# that belongs to another tenant is reported exactly like one that does not
# exist (404). No request field selects the tenant.


class CapaCreateRequest(BaseModel):
    title: str
    source: Optional[str] = "manual"
    description: Optional[str] = None
    risk_level: Optional[str] = "medium"
    owner: Optional[str] = None
    due_date: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None
    status: Optional[str] = "open"


class CapaUpdateRequest(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    risk_level: Optional[str] = None
    description: Optional[str] = None
    corrective_action: Optional[str] = None
    preventive_action: Optional[str] = None


class AuditSignalCapaRequest(BaseModel):
    event_type: Optional[str] = "Audit Signal"
    event_summary: Optional[str] = None
    description: Optional[str] = None
    risk_level: Optional[str] = "medium"
    owner: Optional[str] = None
    due_date: Optional[str] = None
    metadata: Optional[Dict] = None


@router.get("/capa/health")
def capa_health(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "viewer")),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    return {
        "status": "healthy",
        "module": "capa_workflow",
        "version": "1.0.0",
        "capabilities": {
            "create_capa": "ready",
            "list_capas": "ready",
            "audit_signal_to_capa": "ready",
            "governance_summary": "ready",
        },
        "summary": capa_summary(tenant_id=tenant_id),
    }


@router.get("/capa")
def get_capas(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "viewer")),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    items = list_capas(limit=limit, tenant_id=tenant_id)

    return {
        "status": "success",
        "module": "capa_workflow",
        "limit": limit,
        "total_returned": len(items),
        "summary": capa_summary(tenant_id=tenant_id),
        "items": items,
    }


@router.post("/capa")
def post_capa(
    payload: CapaCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    capa = create_capa(**payload.model_dump(), tenant_id=tenant_id)

    return {
        "status": "success",
        "module": "capa_workflow",
        "message": "CAPA created successfully.",
        "capa": capa,
    }


@router.post("/capa/from-audit-signal")
def post_capa_from_audit_signal(
    payload: AuditSignalCapaRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    capa = create_capa_from_audit_signal(payload.model_dump(), tenant_id=tenant_id)

    return {
        "status": "success",
        "module": "capa_workflow",
        "message": "CAPA created from audit signal.",
        "capa": capa,
    }




@router.get("/capa/escalation-summary")
def get_capa_escalation_summary(
    request: Request,
    days_until_due: int = Query(default=7, ge=0, le=90),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    return capa_escalation_summary(days_until_due=days_until_due, tenant_id=tenant_id)



@router.get("/capa/powerbi-csv")
def get_capa_powerbi_csv(
    request: Request,
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    rows = build_capa_powerbi_rows(limit=limit, tenant_id=tenant_id)

    fieldnames = [
        "capa_id",
        "title",
        "source",
        "risk_level",
        "status",
        "owner",
        "due_date",
        "created_at",
        "updated_at",
        "days_to_due",
        "is_overdue",
        "is_high_risk",
        "is_open",
        "corrective_action",
        "preventive_action",
        "description",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    csv_content = output.getvalue()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-capa-powerbi.csv"
        },
    )



@router.get("/capa/governance-scorecard")
def get_capa_governance_scorecard(
    request: Request,
    days_until_due: int = Query(default=7, ge=0, le=90),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    return capa_governance_scorecard(days_until_due=days_until_due, tenant_id=tenant_id)


@router.get("/capa/{capa_id}")
def get_capa_by_id(
    capa_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "viewer")),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    capa = get_capa(capa_id, tenant_id=tenant_id)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")

    return {
        "status": "success",
        "module": "capa_workflow",
        "capa": capa,
    }


@router.patch("/capa/{capa_id}")
def patch_capa(
    capa_id: str,
    payload: CapaUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No update fields provided")

    capa = update_capa(capa_id=capa_id, **updates, tenant_id=tenant_id)
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")

    return {
        "status": "success",
        "module": "capa_workflow",
        "message": "CAPA updated successfully.",
        "capa": capa,
    }
