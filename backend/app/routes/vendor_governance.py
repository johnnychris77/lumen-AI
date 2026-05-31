from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.services.vendor_governance_service import (
    create_vendor_event,
    list_vendor_events,
    vendor_governance_summary,
    get_vendor_event,
    link_vendor_event_to_capa,
    create_capa_from_vendor_event,
    vendor_capa_linkage_summary,
)


router = APIRouter(tags=["vendor-governance"])


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
        "summary": vendor_governance_summary(),
        "message": "Vendor Governance module is deployed and healthy.",
    }


@router.post("/enterprise/vendor-governance/events")
def create_vendor_governance_event(payload: VendorEventRequest):
    event = create_vendor_event(
        vendor_name=payload.vendor_name,
        event_type=payload.event_type,
        event_summary=payload.event_summary,
        risk_level=payload.risk_level,
        site=payload.site,
        device_or_tray=payload.device_or_tray,
        owner=payload.owner,
        capa_id=payload.capa_id,
    )

    return {
        "status": "success",
        "module": "vendor_governance",
        "message": "Vendor governance event created.",
        "event": event,
    }


@router.get("/enterprise/vendor-governance/events")
def get_vendor_governance_events(limit: int = Query(default=50, ge=1, le=500)):
    items = list_vendor_events(limit=limit)

    return {
        "status": "success",
        "module": "vendor_governance",
        "limit": limit,
        "total_returned": len(items),
        "summary": vendor_governance_summary(),
        "items": items,
    }


@router.get("/enterprise/vendor-governance/summary")
def get_vendor_governance_summary():
    return {
        "status": "success",
        "module": "vendor_governance",
        "version": "1.0.0",
        "summary": vendor_governance_summary(),
        "message": "Vendor governance summary generated successfully.",
    }


@router.get("/enterprise/vendor-governance/capa-linkage-summary")
def get_vendor_capa_linkage_summary():
    return {
        "status": "success",
        "module": "vendor_governance",
        "version": "1.0.0",
        "summary": vendor_capa_linkage_summary(),
        "message": "Vendor CAPA linkage summary generated successfully.",
    }


@router.post("/enterprise/vendor-governance/events/{event_id}/link-capa")
def link_vendor_event_to_existing_capa(event_id: str, payload: VendorCapaLinkRequest):
    event = link_vendor_event_to_capa(event_id=event_id, capa_id=payload.capa_id)

    if not event:
        raise HTTPException(status_code=404, detail="Vendor event not found")

    return {
        "status": "success",
        "module": "vendor_governance",
        "message": "Vendor event linked to CAPA.",
        "event": event,
    }


@router.post("/enterprise/vendor-governance/events/{event_id}/create-capa")
def create_capa_for_vendor_event(event_id: str):
    result = create_capa_from_vendor_event(event_id)

    if not result:
        raise HTTPException(status_code=404, detail="Vendor event not found")

    return {
        "status": "success",
        "module": "vendor_governance",
        "message": "CAPA created and linked to vendor event.",
        "vendor_event": result["vendor_event"],
        "capa": result["capa"],
    }
