"""Executive dashboard endpoints — role-specific KPI views for C-suite and department heads."""
import hashlib
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth

router = APIRouter(prefix="/api/executive", tags=["executive"])

ROLES = [
    "spd_director",
    "market_director",
    "infection_prevention",
    "quality_leadership",
    "coo",
    "cno",
    "cfo",
]


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]  # noqa: S324
    return random.Random(int(h, 16))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_tenant(request: Request) -> str:
    return getattr(request.state, "tenant_id", "default")


@router.get("/dashboard/{role}")
async def executive_dashboard(
    role: str,
    request: Request,
    facility_id: str = "",
    period: str = "30d",
    db: Session = Depends(get_db),
) -> dict:
    """Role-specific executive KPI dashboard."""
    require_enterprise_auth(request)
    tenant_id = _get_tenant(request)

    if role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Unknown role. Valid: {ROLES}")

    rng = _seed(f"exec:{tenant_id}:{role}:{facility_id}:{period}")

    # Core KPIs available to all roles
    base_kpis: dict = {
        "tenant_id": tenant_id,
        "facility_id": facility_id,
        "role": role,
        "period": period,
        "generated_at": _now(),
        "inspection_volume": rng.randint(800, 3500),
        "contamination_detection_rate_pct": round(rng.uniform(4.5, 12.0), 1),
        "compliance_score": round(rng.uniform(72.0, 96.0), 1),
        "baseline_adoption_pct": round(rng.uniform(65.0, 95.0), 1),
        "data_source": "mock",
    }

    # Role-specific KPIs
    role_kpis: dict[str, dict] = {
        "spd_director": {
            "technician_throughput_per_hour": round(rng.uniform(18, 35), 1),
            "ai_technician_agreement_rate_pct": round(rng.uniform(85, 94), 1),
            "escalations_this_period": rng.randint(2, 18),
            "protocol_compliance_pct": round(rng.uniform(88, 99), 1),
            "top_defect_categories": ["blood", "corrosion", "residue"],
            "instruments_quarantined": rng.randint(1, 12),
        },
        "infection_prevention": {
            "contamination_events_flagged": rng.randint(15, 80),
            "critical_findings_count": rng.randint(1, 8),
            "critical_fn_rate_pct": round(rng.uniform(0.5, 2.0), 2),
            "escalations_resolved_pct": round(rng.uniform(90, 100), 1),
            "recall_alerts_active": rng.randint(0, 3),
            "jc_ic_score": round(rng.uniform(75, 98), 1),
        },
        "quality_leadership": {
            "jc_readiness_score": round(rng.uniform(72, 97), 1),
            "aami_readiness_score": round(rng.uniform(68, 95), 1),
            "open_capas": rng.randint(0, 8),
            "audit_packages_generated": rng.randint(1, 6),
            "override_rate_pct": round(rng.uniform(2, 12), 1),
            "deficiency_findings": rng.randint(2, 15),
        },
        "coo": {
            "spd_throughput_per_hour": round(rng.uniform(20, 40), 1),
            "bottleneck_station": rng.choice(
                ["Decontamination Bay 1", "Sterilizer 2", "Inspection Station A"]
            ),
            "utilization_pct": round(rng.uniform(55, 90), 1),
            "avg_cycle_time_minutes": round(rng.uniform(55, 130), 1),
            "predicted_repair_avoidance_usd": round(rng.uniform(12000, 85000), 0),
            "instruments_at_risk": rng.randint(3, 22),
        },
        "cno": {
            "infection_risk_reduction_pct": round(rng.uniform(8, 28), 1),
            "ssi_associated_instrument_flags": rng.randint(0, 4),
            "staff_adoption_pct": round(rng.uniform(70, 96), 1),
            "copilot_sessions_completed": rng.randint(50, 400),
            "critical_finding_escalation_rate_pct": round(rng.uniform(1, 5), 1),
        },
        "cfo": {
            "labor_savings_usd": round(rng.uniform(8000, 65000), 0),
            "instrument_replacement_savings_usd": round(rng.uniform(5000, 40000), 0),
            "audit_prep_savings_usd": round(rng.uniform(3000, 20000), 0),
            "repair_avoidance_savings_usd": round(rng.uniform(10000, 75000), 0),
            "total_roi_usd": round(rng.uniform(26000, 200000), 0),
            "subscription_cost_usd": 78000,
            "roi_multiple": round(rng.uniform(1.5, 4.5), 2),
        },
        "market_director": {
            "facilities_active": rng.randint(1, 8),
            "network_benchmarking_rank_pct": round(rng.uniform(40, 90), 1),
            "vendor_scorecard_avg": round(rng.uniform(72, 94), 1),
            "manufacturer_defect_trends": rng.randint(0, 5),
            "cross_facility_contamination_signals": rng.randint(0, 3),
        },
    }

    return {**base_kpis, **role_kpis.get(role, {})}


@router.get("/summary")
async def executive_summary(
    request: Request,
    facility_id: str = "",
    db: Session = Depends(get_db),
) -> dict:
    """Cross-role executive summary — all roles in one response."""
    require_enterprise_auth(request)
    tenant_id = _get_tenant(request)
    rng = _seed(f"execsum:{tenant_id}:{facility_id}")

    return {
        "tenant_id": tenant_id,
        "facility_id": facility_id,
        "generated_at": _now(),
        "data_source": "mock",
        "headline_kpis": {
            "inspection_volume_30d": rng.randint(1200, 4500),
            "contamination_rate_pct": round(rng.uniform(5, 12), 1),
            "jc_readiness_score": round(rng.uniform(75, 97), 1),
            "total_roi_usd_ytd": round(rng.uniform(50000, 350000), 0),
            "instruments_at_risk": rng.randint(3, 25),
            "open_escalations": rng.randint(0, 8),
            "baseline_adoption_pct": round(rng.uniform(70, 96), 1),
        },
        "available_roles": ROLES,
        "role_dashboard_url": "/api/executive/dashboard/{role}",
    }
