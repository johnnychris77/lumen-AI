"""P6: Shared Intelligence API routes (cross-hospital anonymized signals, recalls, dashboard)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.services.vendor_intelligence_engine import (
    _current_period_label,
    compute_capa_effectiveness,
    compute_intelligence_dashboard,
    get_active_recalls,
    get_cross_hospital_trends,
    get_instrument_risk_patterns,
    get_recall_by_id,
    get_shared_defect_signals,
)

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


@router.get("/shared-defects")
def shared_defect_signals(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return anonymized aggregate defect signals — no tenant or hospital identifiers."""
    require_enterprise_auth(request)
    signals = get_shared_defect_signals(limit=limit, db=db)
    return {
        "status": "success",
        "anonymized": True,
        "signals": [s.model_dump() for s in signals],
    }


@router.get("/risk-patterns")
def instrument_risk_patterns(
    request: Request,
    instrument_category: str = Query(default="", description="Filter by category"),
    db: Session = Depends(get_db),
):
    """Return global anonymized instrument risk patterns."""
    require_enterprise_auth(request)
    patterns = get_instrument_risk_patterns(
        instrument_category=instrument_category or None, db=db
    )
    return {
        "status": "success",
        "anonymized": True,
        "patterns": [p.model_dump() for p in patterns],
    }


@router.get("/trending-findings")
def cross_hospital_trending_findings(
    request: Request,
    metric_name: str = Query(default="contamination_rate_pct"),
    n_periods: int = Query(default=6, ge=1, le=24),
    db: Session = Depends(get_db),
):
    """Return anonymized cross-hospital trend data — counts only, no identifiers."""
    require_enterprise_auth(request)
    trends = get_cross_hospital_trends(metric_name=metric_name, n_periods=n_periods, db=db)
    return {
        "status": "success",
        "anonymized": True,
        "metric_name": metric_name,
        "trends": trends,
    }


@router.get("/recalls")
def active_recalls(
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    db: Session = Depends(get_db),
):
    """Return active recall events for a tenant."""
    require_enterprise_auth(request)
    recalls = get_active_recalls(tenant_id, db)
    return {
        "status": "success",
        "tenant_id": tenant_id,
        "recalls": [r.model_dump() for r in recalls],
    }


@router.get("/recalls/{recall_id}")
def recall_detail(
    recall_id: int,
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    db: Session = Depends(get_db),
):
    """Return detail for a single recall event."""
    require_enterprise_auth(request)
    recall = get_recall_by_id(tenant_id, recall_id, db)
    if recall is None:
        raise HTTPException(status_code=404, detail="Recall not found")
    return {"status": "success", "recall": recall.model_dump()}


@router.get("/capa-effectiveness")
def capa_effectiveness(
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    period_label: str = Query(default="", description="Period label"),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Return CAPA effectiveness metrics for a tenant."""
    require_enterprise_auth(request)
    label = period_label or _current_period_label(period_type)
    result = compute_capa_effectiveness(tenant_id, label, db)
    return {"status": "success", "capa_effectiveness": result.model_dump()}


@router.get("/dashboard")
def intelligence_dashboard(
    request: Request,
    tenant_id: str = Query(..., description="Tenant identifier"),
    period_label: str = Query(default="", description="Period label"),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Return the executive intelligence dashboard for a tenant."""
    require_enterprise_auth(request)
    label = period_label or _current_period_label(period_type)
    dashboard = compute_intelligence_dashboard(tenant_id, label, period_type, db)
    return {"status": "success", "dashboard": dashboard.model_dump()}
