"""Phase 14.8 — Predictive Instrument Intelligence endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.services.instrument_intelligence import instrument_timeline

router = APIRouter(tags=["instrument-intelligence"])


@router.get("/instruments/{identifier}/timeline")
def get_instrument_timeline(
    identifier: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    """Inspection timeline + deterministic risk-trend prediction for an
    instrument identifier (barcode or UDI)."""
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    return instrument_timeline(db, identifier, tenant_id)
