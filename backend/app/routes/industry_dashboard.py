"""P15: National SPD Intelligence Network — industry dashboard routes."""
from __future__ import annotations

import hashlib
import random

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id, require_enterprise_auth
from app.models.network_benchmark import NetworkParticipant
from app.services.network_benchmark_service import (
    METRICS,
    compute_industry_benchmarks,
    get_tenant_percentile,
)
from app.services.recall_signal_engine import get_signals_for_tenant

router = APIRouter(prefix="/api/network/dashboard", tags=["industry-dashboard"])


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def _tenant_metrics(tenant_id: str, dashboard_type: str) -> dict:
    """Generate seeded mock tenant metrics."""
    rng = _seed(f"tenant_metrics:{tenant_id}:{dashboard_type}")
    return {
        "contamination_rate": round(rng.uniform(0.01, 0.08), 4),
        "inspection_pass_rate": round(rng.uniform(0.88, 0.99), 4),
        "baseline_adoption_rate": round(rng.uniform(0.70, 0.99), 4),
        "instrument_quality_score": round(rng.uniform(0.80, 0.99), 4),
        "vendor_performance_score": round(rng.uniform(0.75, 0.98), 4),
        "override_rate": round(rng.uniform(0.01, 0.10), 4),
    }


def _build_dashboard(
    db: Session,
    tenant_id: str,
    dashboard_type: str,
) -> dict:
    """Build dashboard payload common structure."""
    benchmarks = compute_industry_benchmarks(db)
    percentiles = [get_tenant_percentile(db, tenant_id, m) for m in METRICS]
    signals = get_signals_for_tenant(db, tenant_id)
    participant_count = (
        db.query(NetworkParticipant)
        .filter(NetworkParticipant.is_active == True)  # noqa: E712
        .count()
    )

    return {
        "status": "success",
        "dashboard_type": dashboard_type,
        "tenant_metrics": _tenant_metrics(tenant_id, dashboard_type),
        "network_benchmarks": benchmarks,
        "tenant_percentile": percentiles,
        "active_recall_signals": len(signals),
        "recall_signal_summary": [
            {"signal_id": s["signal_id"], "instrument_category": s["instrument_category"]}
            for s in signals[:5]
        ],
        "network_participant_count": participant_count,
        "data_source": "mock",
        "tenant_id": None,  # never expose raw tenant_id
    }


def _log_dashboard(db: Session, tenant_id: str, dashboard_type: str) -> None:
    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type=f"network.dashboard_{dashboard_type}_viewed",
        resource_type="industry_dashboard",
        resource_id=dashboard_type,
    )


@router.get("/hospital")
def hospital_dashboard(request: Request, db: Session = Depends(get_db)):
    """Hospital view: my metrics vs network percentiles."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)
    _log_dashboard(db, tenant_id, "hospital")
    return _build_dashboard(db, tenant_id, "hospital")


@router.get("/health-system")
def health_system_dashboard(request: Request, db: Session = Depends(get_db)):
    """Health system view: multi-facility aggregate vs network."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)
    _log_dashboard(db, tenant_id, "health_system")
    return _build_dashboard(db, tenant_id, "health_system")


@router.get("/manufacturer")
def manufacturer_dashboard(request: Request, db: Session = Depends(get_db)):
    """Manufacturer view: their instruments' network defect rates."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)
    _log_dashboard(db, tenant_id, "manufacturer")
    result = _build_dashboard(db, tenant_id, "manufacturer")
    # Manufacturer-specific: add instrument defect summary (anonymized)
    rng = _seed(f"mfr_instruments:{tenant_id}")
    result["instrument_summary"] = [
        {
            "instrument_category": cat,
            "network_defect_rate": round(rng.uniform(0.01, 0.15), 4),
            "network_pass_rate": round(rng.uniform(0.85, 0.99), 4),
            "contributing_facilities": rng.randint(5, 30),
        }
        for cat in ["endoscope", "laparoscopic", "surgical_tray"]
    ]
    return result


@router.get("/vendor")
def vendor_dashboard(request: Request, db: Session = Depends(get_db)):
    """Vendor view: scorecard vs network average."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)
    _log_dashboard(db, tenant_id, "vendor")
    result = _build_dashboard(db, tenant_id, "vendor")
    rng = _seed(f"vendor_scorecard:{tenant_id}")
    result["vendor_scorecard"] = {
        "on_time_delivery_rate": round(rng.uniform(0.88, 0.99), 4),
        "defect_rate": round(rng.uniform(0.01, 0.08), 4),
        "complaint_rate": round(rng.uniform(0.01, 0.05), 4),
        "network_avg_defect_rate": 0.042,
    }
    return result


@router.get("/quality-leader")
def quality_leader_dashboard(request: Request, db: Session = Depends(get_db)):
    """Quality/IP view: contamination trends, recall signals, alerts."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)
    _log_dashboard(db, tenant_id, "quality_leader")
    result = _build_dashboard(db, tenant_id, "quality_leader")
    rng = _seed(f"quality_trends:{tenant_id}")
    result["contamination_trend"] = [
        {"month": f"2025-{m:02d}", "rate": round(rng.uniform(0.02, 0.08), 4)}
        for m in range(1, 7)
    ]
    result["open_alerts"] = rng.randint(0, 5)
    return result
