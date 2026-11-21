import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.tenant_scope import authorized_tenant
from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.services.capa_service import get_capa

from app.services.vendor_governance_service import (
    CapaNotFoundError,
    create_vendor_event,
    list_vendor_events,
    vendor_governance_summary,
    link_vendor_event_to_capa,
    create_capa_from_vendor_event,
    vendor_capa_linkage_summary,
    build_vendor_governance_powerbi_rows,
)


router = APIRouter(tags=["vendor-governance"])

# Tenant isolation (P472-03 AW-10). Every route except the health probe resolves
# the caller's membership-verified tenant inline with
#     authorized_tenant(require_enterprise_auth(request, db=db))
# and passes it to the service. Events are created in, listed from and looked up
# in that tenant only. No request field selects the tenant.


class VendorEventRequest(BaseModel):
    vendor_name: str
    event_type: str
    event_summary: str
    risk_level: str = "medium"
    site: Optional[str] = None
    device_or_tray: Optional[str] = None
    owner: Optional[str] = None
    capa_id: Optional[str] = None


class VendorCapaLinkRequest(BaseModel):
    capa_id: str


@router.get("/enterprise/vendor-governance/health")
def vendor_governance_health():
    return {
        "status": "healthy",
        "module": "vendor_governance",
        "version": "1.0.0",
        "capabilities": {
            "vendor_event_tracking": "ready",
            "vendor_risk_summary": "ready",
            "vendor_capa_linkage": "ready",
            "vendor_governance_summary": "ready",
        },
        # This probe is public, so it carries no governance figures. It used to
        # return event counts and vendor names for every tenant to anonymous callers.
        # Per-tenant figures: GET /api/enterprise/vendor-governance/summary.
        "summary": {},
        "message": "Vendor Governance module is deployed and healthy.",
    }


@router.post("/enterprise/vendor-governance/events")
def create_vendor_governance_event(payload: VendorEventRequest, request: Request, db: Session = Depends(get_db)):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    if payload.capa_id and get_capa(payload.capa_id, tenant_id=tenant_id) is None:
        raise HTTPException(status_code=404, detail="CAPA not found")
    event = create_vendor_event(
        vendor_name=payload.vendor_name,
        event_type=payload.event_type,
        event_summary=payload.event_summary,
        risk_level=payload.risk_level,
        site=payload.site,
        device_or_tray=payload.device_or_tray,
        owner=payload.owner,
        capa_id=payload.capa_id,
        tenant_id=tenant_id,
    )

    return {
        "status": "success",
        "module": "vendor_governance",
        "message": "Vendor governance event created.",
        "event": event,
    }


@router.get("/enterprise/vendor-governance/events")
def get_vendor_governance_events(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    items = list_vendor_events(limit=limit, tenant_id=tenant_id)

    return {
        "status": "success",
        "module": "vendor_governance",
        "limit": limit,
        "total_returned": len(items),
        "summary": vendor_governance_summary(tenant_id=tenant_id),
        "items": items,
    }


@router.get("/enterprise/vendor-governance/summary")
def get_vendor_governance_summary(request: Request, db: Session = Depends(get_db)):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    return {
        "status": "success",
        "module": "vendor_governance",
        "version": "1.0.0",
        "summary": vendor_governance_summary(tenant_id=tenant_id),
        "message": "Vendor governance summary generated successfully.",
    }


@router.get("/enterprise/vendor-governance/capa-linkage-summary")
def get_vendor_capa_linkage_summary(request: Request, db: Session = Depends(get_db)):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    return {
        "status": "success",
        "module": "vendor_governance",
        "version": "1.0.0",
        "summary": vendor_capa_linkage_summary(tenant_id=tenant_id),
        "message": "Vendor CAPA linkage summary generated successfully.",
    }


@router.post("/enterprise/vendor-governance/events/{event_id}/link-capa")
def link_vendor_event_to_existing_capa(
    event_id: str, payload: VendorCapaLinkRequest, request: Request, db: Session = Depends(get_db),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    try:
        event = link_vendor_event_to_capa(event_id=event_id, capa_id=payload.capa_id, tenant_id=tenant_id)
    except CapaNotFoundError:
        raise HTTPException(status_code=404, detail="CAPA not found") from None

    if not event:
        raise HTTPException(status_code=404, detail="Vendor event not found")

    return {
        "status": "success",
        "module": "vendor_governance",
        "message": "Vendor event linked to CAPA.",
        "event": event,
    }


@router.post("/enterprise/vendor-governance/events/{event_id}/create-capa")
def create_capa_for_vendor_event(event_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    result = create_capa_from_vendor_event(event_id, tenant_id=tenant_id)

    if not result:
        raise HTTPException(status_code=404, detail="Vendor event not found")

    return {
        "status": "success",
        "module": "vendor_governance",
        "message": "CAPA created and linked to vendor event.",
        "vendor_event": result["vendor_event"],
        "capa": result["capa"],
    }


@router.get("/enterprise/vendor-governance/powerbi-csv")
def get_vendor_governance_powerbi_csv(
    request: Request,
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
    rows = build_vendor_governance_powerbi_rows(limit=limit, tenant_id=tenant_id)

    fieldnames = [
        "vendor_event_id",
        "vendor_name",
        "event_type",
        "event_summary",
        "risk_level",
        "site",
        "device_or_tray",
        "owner",
        "status",
        "capa_id",
        "is_high_risk",
        "is_linked_to_capa",
        "created_at",
        "updated_at",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for row in rows:
        writer.writerow(row)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=lumenai-vendor-governance-powerbi.csv"
        },
    )
