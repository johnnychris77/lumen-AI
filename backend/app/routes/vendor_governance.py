from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.vendor_governance_service import (
    create_vendor_event,
    list_vendor_events,
    vendor_governance_summary,
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
