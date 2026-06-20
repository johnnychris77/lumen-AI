"""P6: Manufacturer Intelligence API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.services.vendor_intelligence_engine import (
    _current_period_label,
    compute_all_manufacturer_scorecards,
    compute_manufacturer_scorecard,
    compute_manufacturer_trends,
)

router = APIRouter(prefix="/api/manufacturer-intelligence", tags=["manufacturer-intelligence"])


@router.get("/manufacturers")
def list_manufacturer_scorecards(
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    period_label: str = Query(default="", description="Period label"),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """List composite scorecards for all manufacturers within a tenant."""
    require_enterprise_auth(request)
    label = period_label or _current_period_label(period_type)
    scorecards = compute_all_manufacturer_scorecards(tenant_id, label, period_type, db)
    return {"status": "success", "tenant_id": tenant_id, "period_label": label, "manufacturers": [s.model_dump() for s in scorecards]}


@router.get("/manufacturers/{manufacturer_id}")
def get_manufacturer(
    manufacturer_id: str,
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    period_label: str = Query(default="", description="Period label"),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Get scorecard for a specific manufacturer."""
    require_enterprise_auth(request)
    label = period_label or _current_period_label(period_type)
    scorecard = compute_manufacturer_scorecard(tenant_id, manufacturer_id, label, period_type, db)
    return {"status": "success", "manufacturer": scorecard.model_dump()}


@router.get("/manufacturers/{manufacturer_id}/scorecard")
def manufacturer_scorecard(
    manufacturer_id: str,
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    period_label: str = Query(default="", description="Period label"),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Get detailed composite scorecard for a manufacturer."""
    require_enterprise_auth(request)
    label = period_label or _current_period_label(period_type)
    scorecard = compute_manufacturer_scorecard(tenant_id, manufacturer_id, label, period_type, db)
    return {"status": "success", "scorecard": scorecard.model_dump()}


@router.get("/manufacturers/{manufacturer_id}/trends")
def manufacturer_trends(
    manufacturer_id: str,
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    n_periods: int = Query(default=6, ge=1, le=24),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Get defect trend time-series for a manufacturer."""
    require_enterprise_auth(request)
    trends = compute_manufacturer_trends(tenant_id, manufacturer_id, n_periods, period_type, db)
    return {"status": "success", "trends": [t.model_dump() for t in trends]}
