"""v2.8 — LumenAI OR Connect: Vendor Collaboration Portal routes (Section 7).

API prefix: /api/or-connect/vendor-portal. Auth: `require_manufacturer_auth`
(Bearer token + X-Manufacturer-ID header) reused as-is — vendor and
manufacturer are the same external-party identity concept elsewhere in this
codebase. Unlike the existing manufacturer scorecard endpoints (which label
mock data with the caller's id but never filter by it), every endpoint here
filters real rows by that vendor's own name, so a vendor can only ever see
or act on their own trays/repairs.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id, require_manufacturer_auth
from app.services import or_connect_service as engine
from app.services import or_connect_vendor_service as vendor_engine

router = APIRouter(prefix="/api/or-connect/vendor-portal", tags=["or-connect-vendor-portal"])


class DeliveryConfirmIn(BaseModel):
    confirmed_by: str = Field(..., min_length=1, max_length=255)


class ReplacementRequestIn(BaseModel):
    notes: str = ""


def _tenant(request: Request) -> str:
    return get_request_tenant_id(request)


@router.get("")
def get_vendor_portal(
    request: Request, db: Session = Depends(get_db), vendor_id: str = Depends(require_manufacturer_auth),
):
    tenant_id = _tenant(request)
    return vendor_engine.vendor_portal_view(db, tenant_id, vendor_id)


@router.post("/trays/{tray_id}/confirm-delivery")
def post_confirm_delivery(
    tray_id: int, body: DeliveryConfirmIn, request: Request, db: Session = Depends(get_db),
    vendor_id: str = Depends(require_manufacturer_auth),
):
    tenant_id = _tenant(request)
    try:
        return vendor_engine.confirm_delivery(db, tenant_id, vendor_id, tray_id, confirmed_by=body.confirmed_by)
    except engine.CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/trays/{tray_id}/request-replacement")
def post_request_replacement(
    tray_id: int, body: ReplacementRequestIn, request: Request, db: Session = Depends(get_db),
    vendor_id: str = Depends(require_manufacturer_auth),
):
    tenant_id = _tenant(request)
    try:
        return vendor_engine.request_replacement(db, tenant_id, vendor_id, tray_id, notes=body.notes)
    except engine.CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
