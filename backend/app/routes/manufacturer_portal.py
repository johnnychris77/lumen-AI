"""P6: Manufacturer Portal — self-service scorecard and benchmark endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_manufacturer_auth
from app.services.vendor_intelligence_engine import (
    _current_period_label,
    compute_manufacturer_scorecard,
    compute_manufacturer_trends,
    compute_all_manufacturer_scorecards,
)

router = APIRouter(prefix="/api/manufacturer-portal", tags=["manufacturer-portal"])


@router.get("/my-scorecard")
def my_scorecard(
    request: Request,
    period_label: str = Query(default="", description="Period label"),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Return this manufacturer's own scorecard — requires X-Manufacturer-ID header."""
    manufacturer_id = require_manufacturer_auth(request)
    label = period_label or _current_period_label(period_type)
    scorecard = compute_manufacturer_scorecard(
        tenant_id="global",
        manufacturer_id=manufacturer_id,
        period_label=label,
        period_type=period_type,
        db=db,
    )
    return {
        "status": "success",
        "manufacturer_id": manufacturer_id,
        "scorecard": scorecard.model_dump(),
    }


@router.get("/my-defect-trends")
def my_defect_trends(
    request: Request,
    n_periods: int = Query(default=6, ge=1, le=24),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Return defect trends for this manufacturer — requires X-Manufacturer-ID header."""
    manufacturer_id = require_manufacturer_auth(request)
    trends = compute_manufacturer_trends(
        tenant_id="global",
        manufacturer_id=manufacturer_id,
        n_periods=n_periods,
        period_type=period_type,
        db=db,
    )
    return {
        "status": "success",
        "manufacturer_id": manufacturer_id,
        "trends": [t.model_dump() for t in trends],
    }


@router.get("/network-benchmark")
def network_benchmark(
    request: Request,
    period_label: str = Query(default="", description="Period label"),
    period_type: str = Query(default="monthly"),
    db: Session = Depends(get_db),
):
    """Return anonymized network average scores and this manufacturer's relative rank.

    CRITICAL: never includes hospital_id or tenant_id in the response.
    Only aggregate averages and this manufacturer's own score are returned.
    """
    manufacturer_id = require_manufacturer_auth(request)
    label = period_label or _current_period_label(period_type)

    # Get all manufacturer scorecards from mock pool (anonymized — no tenant data)
    all_scorecards = compute_all_manufacturer_scorecards(
        tenant_id="global",
        period_label=label,
        period_type=period_type,
        db=db,
    )

    my_scorecard = compute_manufacturer_scorecard(
        tenant_id="global",
        manufacturer_id=manufacturer_id,
        period_label=label,
        period_type=period_type,
        db=db,
    )

    if all_scorecards:
        avg_score = round(sum(s.composite_score for s in all_scorecards) / len(all_scorecards), 1)
        peer_count = len(all_scorecards)
        my_rank = sum(1 for s in all_scorecards if s.composite_score > my_scorecard.composite_score) + 1
    else:
        avg_score = 0.0
        peer_count = 0
        my_rank = 1

    # Return ONLY anonymized aggregate data — no hospital_id, no tenant_id
    return {
        "status": "success",
        "anonymized": True,
        "manufacturer_id": manufacturer_id,
        "my_composite_score": my_scorecard.composite_score,
        "my_risk_tier": my_scorecard.risk_tier,
        "my_rank": my_rank,
        "network_avg_composite_score": avg_score,
        "network_peer_count": peer_count,
        "period_label": label,
        "period_type": period_type,
    }
