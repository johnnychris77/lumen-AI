"""P6: Vendor Intelligence API routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.services.vendor_intelligence_engine import (
    _current_period_label,
    compute_all_vendor_scorecards,
    compute_vendor_scorecard,
    compute_vendor_trends,
)

router = APIRouter(prefix="/api/vendor-intelligence", tags=["vendor-intelligence"])


@router.get("/vendors")
def list_vendor_scorecards(
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    period_label: str = Query(default="", description="Period label, e.g. 2026-06"),
    period_type: str = Query(default="monthly", description="monthly|quarterly|annual"),
    db: Session = Depends(get_db),
):
    """List composite scorecards for all vendors within a tenant."""
    require_enterprise_auth(request)
    label = period_label or _current_period_label(period_type)
    scorecards = compute_all_vendor_scorecards(tenant_id, label, period_type, db)
    return {"status": "success", "tenant_id": tenant_id, "period_label": label, "vendors": [s.model_dump() for s in scorecards]}


@router.get("/vendors/{vendor_id}")
def get_vendor(
    vendor_id: str,
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    period_label: str = Query(default="", description="Period label"),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Get scorecard for a specific vendor."""
    require_enterprise_auth(request)
    label = period_label or _current_period_label(period_type)
    scorecard = compute_vendor_scorecard(tenant_id, vendor_id, label, period_type, db)
    return {"status": "success", "vendor": scorecard.model_dump()}


@router.get("/vendors/{vendor_id}/scorecard")
def vendor_scorecard(
    vendor_id: str,
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    period_label: str = Query(default="", description="Period label"),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Get detailed composite scorecard for a vendor."""
    require_enterprise_auth(request)
    label = period_label or _current_period_label(period_type)
    scorecard = compute_vendor_scorecard(tenant_id, vendor_id, label, period_type, db)
    return {"status": "success", "scorecard": scorecard.model_dump()}


@router.get("/vendors/{vendor_id}/trends")
def vendor_trends(
    vendor_id: str,
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    n_periods: int = Query(default=6, ge=1, le=24),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Get defect trend time-series for a vendor."""
    require_enterprise_auth(request)
    trends = compute_vendor_trends(tenant_id, vendor_id, n_periods, period_type, db)
    return {"status": "success", "trends": [t.model_dump() for t in trends]}
