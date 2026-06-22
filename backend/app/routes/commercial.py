"""P17: Commercial Launch, Sales Enablement & Market Expansion.

Provides product packaging definitions, pricing models, customer success
health scoring, expansion analytics, and an ROI calculator. Packaging and
pricing align with the established commercial model
(docs/commercial/product-packaging.md and pricing-strategy.md):
Starter / Professional / Enterprise / Health System.

All monetary figures are list estimates for business-case modeling only and
are not quotes. All quality-related outputs remain human-review-required and
make no clinical or regulatory claims.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.db import models

# Reuse the validated pilot ROI constants so the commercial calculator and the
# pilot analytics stay consistent.
from app.routes.pilot_analytics import (
    MINUTES_SAVED_PER_INSPECTION,
    STAFF_COST_PER_HOUR_USD,
    REPROCESSING_COST_USD,
    SURGICAL_CANCELLATION_COST_USD,
)

router = APIRouter(prefix="/api/commercial", tags=["commercial"])

# ---------------------------------------------------------------------------
# Phase 1 — Product Packaging (aligned with docs/commercial/product-packaging.md)
# ---------------------------------------------------------------------------

PACKAGES = {
    "starter": {
        "tier": "starter",
        "name": "LumenAI Starter",
        "target": "Single-facility community hospitals, pilot programs",
        "facilities": "1",
        "users": "Up to 10 SPD users",
        "inspection_volume": "Up to 2,000 inspections/month",
        "features": [
            "AI lumen inspection (blood, tissue, residue detection)",
            "Baseline library (up to 500 baselines)",
            "Basic AI ranking (top 20 priority queue)",
            "Self-comparison benchmarking",
            "PDF export",
            "Audit log (1-year retention)",
        ],
        "excluded": ["Vendor intelligence", "Predictive analytics", "Copilot", "Digital twin"],
        "support": "Email, 5-day SLA",
    },
    "professional": {
        "tier": "professional",
        "name": "LumenAI Professional",
        "target": "Mid-size hospitals, multi-OR facilities, regional medical centers",
        "facilities": "Up to 3",
        "users": "Up to 30 SPD users",
        "inspection_volume": "Up to 10,000 inspections/month",
        "features": [
            "All 12 AI finding categories",
            "Full priority ranking + trend analysis",
            "Peer hospital benchmarking (anonymized)",
            "Vendor scorecards + defect trends",
            "Predictive analytics (failure, contamination recurrence)",
            "Guided inspection copilot",
            "Full regulatory readiness (JC/AAMI/CMS/FDA/ISO)",
            "Audit log (3-year retention)",
        ],
        "excluded": ["Autonomous copilot", "Manufacturer portal", "API access", "SSO/OIDC"],
        "support": "Email + phone, 2-day SLA, named CSM",
    },
    "enterprise": {
        "tier": "enterprise",
        "name": "LumenAI Enterprise",
        "target": "Academic medical centers, large hospital systems (3–10 facilities)",
        "facilities": "Up to 10",
        "users": "Up to 100 SPD users",
        "inspection_volume": "Unlimited",
        "features": [
            "Everything in Professional",
            "Manufacturer benchmarking + recall integration",
            "Full predictive suite",
            "Guided + autonomous + audit copilot modes",
            "Full digital twin (what-if simulation)",
            "Manufacturer portal",
            "REST API for EHR/EMR/CMMS integration",
            "Audit log (7-year retention)",
            "Enterprise hierarchy, onboarding, baseline distribution, executive scorecards",
        ],
        "excluded": ["Unlimited facilities", "SSO/OIDC", "Dedicated infrastructure"],
        "support": "Dedicated CSM, 4-hour SLA, quarterly business reviews",
    },
    "health_system": {
        "tier": "health_system",
        "name": "LumenAI Health System",
        "target": "IDNs, multi-hospital networks, GPO members (10+ facilities)",
        "facilities": "Unlimited",
        "users": "Unlimited",
        "inspection_volume": "Unlimited",
        "features": [
            "Everything in Enterprise",
            "Network-wide + cross-system anonymized benchmarking",
            "SSO/OIDC (Epic, Azure AD, Okta)",
            "CMMS integration (ServiceMax, IBM Maximo, TDSi)",
            "HIPAA BAA",
            "Dedicated infrastructure (private cloud / on-prem K8s)",
            "C-suite executive dashboards (COO, CNO, CFO, CMO)",
            "Audit log (10-year retention)",
            "Professional services (implementation, training, integrations)",
        ],
        "excluded": [],
        "support": "Executive sponsor, 1-hour SLA, monthly reviews",
        "data_governance": (
            "Cross-system benchmarking uses anonymized data only. No tenant can view "
            "another tenant's raw data. Every cross-organization data action is "
            "audit-logged. All signals are candidate indicators requiring human review."
        ),
    },
}

# ---------------------------------------------------------------------------
# Phase 2 — Pricing models (list estimates only; see pricing-strategy.md)
# ---------------------------------------------------------------------------

HOSPITAL_PRICING = {
    "model": "per_facility_subscription",
    "currency": "USD",
    "billing": "annual (monthly available at 20% premium)",
    "tiers": {
        "starter": {"base_annual": 30000, "included_facilities": 1,
                    "additional_facility_annual": None},
        "professional": {"base_annual": 78000, "included_facilities": 3,
                         "additional_facility_annual": 18000},
        "enterprise": {"base_annual": 180000, "included_facilities": 10,
                       "additional_facility_annual": 12000},
        "health_system": {"base_annual": "custom",
                          "range_annual": [250000, 800000],
                          "implementation_fee": [15000, 50000]},
    },
    "multi_year_discounts": [
        {"term_years": 2, "discount_pct": 10},
        {"term_years": 3, "discount_pct": 15},
    ],
    "multi_facility_discounts": [
        {"facility_band": "3-5", "discount_pct": 10},
        {"facility_band": "6+", "discount_pct": 20},
    ],
    "notes": "List estimates for modeling only; not a quote.",
}

VENDOR_PRICING = {
    "model": "manufacturer_subscription",
    "currency": "USD",
    "billing": "annual",
    "tiers": {
        "manufacturer_portal": {"base_annual": 6000,
                                "description": "Manufacturers access their own scorecard"},
        "vendor_intelligence_premium": {"base_annual": 12000,
                                        "description": "Included in Professional+",
                                        "extras": ["vendor scorecards", "defect trends",
                                                   "FDA recall integration"]},
    },
    "notes": "Vendors publish manufacturer baselines; hospital approval still required.",
}

ENTERPRISE_PRICING = {
    "model": "per_facility_tiered",
    "currency": "USD",
    "billing": "annual",
    "enterprise_base_annual": 180000,
    "enterprise_included_facilities": 10,
    "enterprise_additional_facility_annual": 12000,
    "health_system_range_annual": [250000, 800000],
    "implementation_fee_range": [15000, 50000],
    "multi_year_discounts": HOSPITAL_PRICING["multi_year_discounts"],
    "multi_facility_discounts": HOSPITAL_PRICING["multi_facility_discounts"],
    "notes": "List estimates for modeling only; not a quote.",
}


def _multi_facility_discount(num_facilities: int) -> float:
    """Return the multi-facility discount fraction (0.0–1.0)."""
    if num_facilities >= 6:
        return 0.20
    if num_facilities >= 3:
        return 0.10
    return 0.0


def _multi_year_discount(term_years: int) -> float:
    if term_years >= 3:
        return 0.15
    if term_years >= 2:
        return 0.10
    return 0.0


def _recommend_tier(num_facilities: int) -> str:
    if num_facilities <= 1:
        return "starter"
    if num_facilities <= 3:
        return "professional"
    if num_facilities <= 10:
        return "enterprise"
    return "health_system"


def _model_annual_cost(tier: str, num_facilities: int) -> float | None:
    """Model gross annual list cost for a tier. Health System is custom (returns
    the midpoint of its published range)."""
    if tier == "starter":
        return 30000.0 * max(1, num_facilities)
    if tier == "professional":
        extra = max(0, num_facilities - 3)
        return 78000.0 + extra * 18000.0
    if tier == "enterprise":
        extra = max(0, num_facilities - 10)
        return 180000.0 + extra * 12000.0
    if tier == "health_system":
        return float(sum(ENTERPRISE_PRICING["health_system_range_annual"]) / 2)
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_range(days: int):
    now = datetime.now(timezone.utc)
    return now - timedelta(days=days), now


def _rag(value: float, target: float) -> str:
    if value >= target:
        return "green"
    if value >= 0.8 * target:
        return "amber"
    return "red"


# ---------------------------------------------------------------------------
# Phase 1 endpoints — Packaging
# ---------------------------------------------------------------------------

@router.get("/packages")
def list_packages(_=Depends(require_roles("admin", "executive", "spd_manager"))):
    return {"packages": list(PACKAGES.values()), "count": len(PACKAGES)}


@router.get("/packages/{tier}")
def get_package(tier: str, _=Depends(require_roles("admin", "executive", "spd_manager"))):
    pkg = PACKAGES.get(tier)
    if not pkg:
        raise HTTPException(status_code=404, detail=f"Unknown package tier '{tier}'")
    return pkg


# ---------------------------------------------------------------------------
# Phase 2 endpoints — Pricing
# ---------------------------------------------------------------------------

@router.get("/pricing/hospital")
def hospital_pricing(_=Depends(require_roles("admin", "executive"))):
    return HOSPITAL_PRICING


@router.get("/pricing/vendor")
def vendor_pricing(_=Depends(require_roles("admin", "executive"))):
    return VENDOR_PRICING


@router.get("/pricing/enterprise")
def enterprise_pricing(_=Depends(require_roles("admin", "executive"))):
    return ENTERPRISE_PRICING


class QuoteRequest(BaseModel):
    tier: str | None = Field(default=None)
    num_facilities: int = Field(default=1, ge=1)
    term_years: int = Field(default=1, ge=1, le=5)


@router.post("/pricing/estimate")
def pricing_estimate(
    payload: QuoteRequest,
    _=Depends(require_roles("admin", "executive")),
):
    """Produce a non-binding list-price estimate for modeling."""
    tier = payload.tier or _recommend_tier(payload.num_facilities)
    gross = _model_annual_cost(tier, payload.num_facilities)
    if gross is None:
        raise HTTPException(status_code=404, detail=f"Unknown tier '{tier}'")

    fac_disc = _multi_facility_discount(payload.num_facilities)
    yr_disc = _multi_year_discount(payload.term_years)
    # Discounts apply on the base; take the larger facility discount plus
    # the multi-year discount, capped to avoid double-deep stacking.
    total_disc = min(0.40, fac_disc + yr_disc)
    net = round(gross * (1.0 - total_disc), 2)

    return {
        "tier": tier,
        "recommended_tier": _recommend_tier(payload.num_facilities),
        "num_facilities": payload.num_facilities,
        "term_years": payload.term_years,
        "gross_annual_usd": round(gross, 2),
        "multi_facility_discount_pct": round(fac_disc * 100, 1),
        "multi_year_discount_pct": round(yr_disc * 100, 1),
        "total_discount_pct": round(total_disc * 100, 1),
        "net_annual_usd": net,
        "currency": "USD",
        "disclaimer": "Non-binding list estimate for modeling only; not a quote. "
                      "Health System pricing is custom; figure shown is range midpoint.",
    }


# ---------------------------------------------------------------------------
# Phase 3 — Customer Success: adoption / onboarding / training / health score
# ---------------------------------------------------------------------------

# Health score weights (sum = 1.0)
_HEALTH_WEIGHTS = {
    "adoption": 0.30,
    "onboarding": 0.20,
    "training": 0.20,
    "utilization": 0.30,
}

_HEALTH_THRESHOLDS = {"healthy": 80.0, "watch": 60.0}

# Inspection volume that represents "fully utilized" for a 30-day window.
_FULL_UTILIZATION_30D = 200


def _inspection_count(db: Session, tenant_id: str | None, days: int) -> int:
    start, end = _date_range(days)
    q = db.query(sqlfunc.count(models.Inspection.id)).filter(
        models.Inspection.created_at >= start,
        models.Inspection.created_at <= end,
    )
    if tenant_id:
        q = q.filter(models.Inspection.tenant_id == tenant_id)
    return int(q.scalar() or 0)


def _active_users(db: Session, tenant_id: str | None) -> int:
    q = db.query(sqlfunc.count(models.TenantMembership.id)).filter(
        models.TenantMembership.is_enabled.is_(True)
    )
    if tenant_id:
        q = q.filter(models.TenantMembership.tenant_id == tenant_id)
    return int(q.scalar() or 0)


def _latest_snapshot(db: Session, tenant_id: str | None):
    q = db.query(models.CustomerSuccessSnapshot)
    if tenant_id:
        q = q.filter(models.CustomerSuccessSnapshot.tenant_id == tenant_id)
    return q.order_by(models.CustomerSuccessSnapshot.captured_at.desc()).first()


def _compute_health(db: Session, tenant_id: str | None,
                    onboarding_pct: float, training_pct: float) -> dict:
    """Pure-ish health computation shared by the GET endpoint and snapshot POST."""
    insp_30 = _inspection_count(db, tenant_id, 30)
    insp_prev_30 = _inspection_count(db, tenant_id, 60) - insp_30
    users = _active_users(db, tenant_id)

    adoption_pct = 0.0
    if users > 0:
        adoption_pct = min(100.0, (insp_30 / users) * 10.0)
    utilization_pct = min(100.0, (insp_30 / _FULL_UTILIZATION_30D) * 100.0)

    dims = {
        "adoption": round(adoption_pct, 1),
        "onboarding": round(onboarding_pct, 1),
        "training": round(training_pct, 1),
        "utilization": round(utilization_pct, 1),
    }
    composite = round(sum(dims[k] * w for k, w in _HEALTH_WEIGHTS.items()), 1)

    if composite >= _HEALTH_THRESHOLDS["healthy"]:
        status_label = "healthy"
    elif composite >= _HEALTH_THRESHOLDS["watch"]:
        status_label = "watch"
    else:
        status_label = "at_risk"

    trend = "flat"
    if insp_prev_30 > 0:
        change = (insp_30 - insp_prev_30) / insp_prev_30
        trend = "up" if change > 0.1 else "down" if change < -0.1 else "flat"

    return {
        "tenant_id": tenant_id,
        "dimensions": dims,
        "weights": _HEALTH_WEIGHTS,
        "composite_score": composite,
        "status": status_label,
        "inspection_trend": trend,
        "inspections_last_30d": insp_30,
        "inspections_prev_30d": max(0, insp_prev_30),
        "active_users": users,
        "human_review_required": True,
        "disclaimer": "Health score is an operational indicator for CSM triage, not a clinical measure.",
    }


@router.get("/customer-success/health-score")
def health_score(
    tenant_id: str | None = Query(default=None),
    onboarding_pct: float | None = Query(default=None, ge=0, le=100),
    training_pct: float | None = Query(default=None, ge=0, le=100),
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Composite customer health score (0–100) for renewal/expansion triage.

    onboarding_pct / training_pct precedence: explicit query params override;
    otherwise the latest persisted snapshot is used; otherwise default 100.
    """
    snap = _latest_snapshot(db, tenant_id)
    o_pct = onboarding_pct if onboarding_pct is not None else (
        snap.onboarding_pct if snap else 100.0)
    t_pct = training_pct if training_pct is not None else (
        snap.training_pct if snap else 100.0)

    result = _compute_health(db, tenant_id, o_pct, t_pct)
    result["source"] = ("query" if (onboarding_pct is not None or training_pct is not None)
                        else "snapshot" if snap else "default")
    if snap:
        result["last_snapshot_at"] = snap.captured_at.isoformat()
    return result


class SnapshotRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    onboarding_pct: float = Field(default=100.0, ge=0, le=100)
    training_pct: float = Field(default=100.0, ge=0, le=100)


@router.post("/customer-success/snapshot", status_code=201)
def create_snapshot(
    payload: SnapshotRequest,
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Persist a customer-success snapshot so health scores are reproducible and
    trendable. Audit-logged."""
    health = _compute_health(db, payload.tenant_id, payload.onboarding_pct, payload.training_pct)
    snap = models.CustomerSuccessSnapshot(
        tenant_id=payload.tenant_id,
        captured_by=getattr(current_user, "email", "unknown"),
        onboarding_pct=payload.onboarding_pct,
        training_pct=payload.training_pct,
        adoption_pct=health["dimensions"]["adoption"],
        utilization_pct=health["dimensions"]["utilization"],
        composite_score=health["composite_score"],
        status=health["status"],
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    try:
        log_audit_event(
            db,
            tenant_id=payload.tenant_id,
            tenant_name="Commercial",
            actor_email=getattr(current_user, "email", "unknown"),
            actor_role=getattr(current_user, "role", "executive"),
            action_type="customer_success_snapshot_created",
            resource_type="customer_success_snapshot",
            resource_id=str(snap.id),
            details={"composite_score": health["composite_score"], "status": health["status"]},
            compliance_flag=True,
        )
    except Exception:
        pass

    return {
        "id": snap.id,
        "tenant_id": snap.tenant_id,
        "captured_at": snap.captured_at.isoformat(),
        "composite_score": snap.composite_score,
        "status": snap.status,
        "dimensions": health["dimensions"],
    }


@router.get("/customer-success/trend")
def health_trend(
    tenant_id: str = Query(..., min_length=1),
    limit: int = Query(default=24, ge=1, le=200),
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Return persisted health-score snapshots over time for a tenant."""
    rows = (
        db.query(models.CustomerSuccessSnapshot)
        .filter(models.CustomerSuccessSnapshot.tenant_id == tenant_id)
        .order_by(models.CustomerSuccessSnapshot.captured_at.desc())
        .limit(limit)
        .all()
    )
    series = [
        {
            "captured_at": r.captured_at.isoformat(),
            "composite_score": r.composite_score,
            "status": r.status,
            "onboarding_pct": r.onboarding_pct,
            "training_pct": r.training_pct,
            "adoption_pct": r.adoption_pct,
            "utilization_pct": r.utilization_pct,
        }
        for r in reversed(rows)
    ]
    return {"tenant_id": tenant_id, "count": len(series), "series": series}


@router.get("/customer-success/onboarding-status")
def onboarding_status(
    system_id: str | None = Query(default=None),
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Roll up enterprise onboarding workflow completion for CSM tracking."""
    q = db.query(models.OnboardingWorkflow)
    if system_id:
        q = q.filter(models.OnboardingWorkflow.system_id == system_id)
    workflows = q.all()

    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    completed = 0
    for w in workflows:
        st = getattr(w, "status", "unknown") or "unknown"
        wt = getattr(w, "workflow_type", "unknown") or "unknown"
        by_status[st] = by_status.get(st, 0) + 1
        by_type[wt] = by_type.get(wt, 0) + 1
        if st == "completed":
            completed += 1

    total = len(workflows)
    return {
        "system_id": system_id,
        "total_workflows": total,
        "completed": completed,
        "completion_pct": round((completed / total * 100) if total else 0.0, 1),
        "by_status": by_status,
        "by_type": by_type,
    }


# ---------------------------------------------------------------------------
# Phase 5 — Expansion Analytics
# ---------------------------------------------------------------------------

@router.get("/expansion/opportunities")
def expansion_opportunities(
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Identify candidate expansion opportunities and renewal-risk signals.

    All signals are candidate indicators for human review by the account team.
    """
    rows = (
        db.query(
            models.Inspection.tenant_id,
            sqlfunc.count(models.Inspection.id),
        )
        .group_by(models.Inspection.tenant_id)
        .all()
    )

    opportunities = []
    renewal_risks = []
    for tenant_id, _count in rows:
        if not tenant_id:
            continue
        insp_30 = _inspection_count(db, tenant_id, 30)
        insp_prev_30 = _inspection_count(db, tenant_id, 60) - insp_30
        utilization_pct = min(100.0, (insp_30 / _FULL_UTILIZATION_30D) * 100.0)

        snap = _latest_snapshot(db, tenant_id)
        health_status = snap.status if snap else None

        # Strong upsell candidates are high-utilization AND not at-risk.
        if utilization_pct >= 80.0 and health_status != "at_risk":
            opportunities.append({
                "tenant_id": tenant_id,
                "signal": "high_utilization",
                "utilization_pct": round(utilization_pct, 1),
                "health_status": health_status,
                "recommended_action": "Upsell capacity / upgrade tier (human review)",
            })

        # Renewal risk from declining activity OR a persisted at-risk health score.
        change = (insp_30 - insp_prev_30) / insp_prev_30 if insp_prev_30 > 0 else 0.0
        if (insp_prev_30 > 0 and change <= -0.25) or health_status == "at_risk":
            renewal_risks.append({
                "tenant_id": tenant_id,
                "signal": "at_risk_health" if health_status == "at_risk" else "declining_activity",
                "change_pct": round(change * 100, 1),
                "health_status": health_status,
                "recommended_action": "CSM outreach / adoption review (human review)",
            })

    return {
        "opportunities": opportunities,
        "renewal_risks": renewal_risks,
        "opportunity_count": len(opportunities),
        "renewal_risk_count": len(renewal_risks),
        "human_review_required": True,
        "disclaimer": "Candidate commercial signals for account-team review only.",
    }


# ---------------------------------------------------------------------------
# Phase 4 & 6 — ROI calculator / Executive business case
# ---------------------------------------------------------------------------

class ROIRequest(BaseModel):
    monthly_inspections: int = Field(default=2000, ge=0)
    contamination_rate: float = Field(default=0.06, ge=0, le=1)
    num_facilities: int = Field(default=1, ge=1)
    tier: str | None = Field(default=None)
    annual_subscription_usd: float | None = Field(default=None, ge=0)
    term_years: int = Field(default=1, ge=1, le=5)


@router.post("/roi/calculate")
def roi_calculate(
    payload: ROIRequest,
    _=Depends(require_roles("admin", "executive")),
):
    """Sales/business-case ROI calculator using validated pilot constants.

    All figures are estimates for modeling. Reprocessing and cancellation
    avoidance assume conservative capture fractions and require organizational
    validation before use in a contract.
    """
    annual_inspections = payload.monthly_inspections * 12 * payload.num_facilities

    minutes_saved = annual_inspections * MINUTES_SAVED_PER_INSPECTION
    labor_saved_usd = (minutes_saved / 60.0) * STAFF_COST_PER_HOUR_USD

    contamination_events = annual_inspections * payload.contamination_rate
    reprocessing_avoided = contamination_events * 0.60
    reprocessing_savings_usd = reprocessing_avoided * REPROCESSING_COST_USD
    cancellations_avoided = contamination_events * 0.01
    cancellation_savings_usd = cancellations_avoided * SURGICAL_CANCELLATION_COST_USD

    gross_benefit = labor_saved_usd + reprocessing_savings_usd + cancellation_savings_usd

    if payload.annual_subscription_usd is not None:
        cost = payload.annual_subscription_usd
    else:
        tier = payload.tier or _recommend_tier(payload.num_facilities)
        modeled = _model_annual_cost(tier, payload.num_facilities) or 0.0
        disc = min(0.40, _multi_facility_discount(payload.num_facilities)
                   + _multi_year_discount(payload.term_years))
        cost = modeled * (1.0 - disc)

    net_benefit = gross_benefit - cost
    roi_pct = round((net_benefit / cost * 100), 1) if cost > 0 else None
    payback_months = round((cost / (gross_benefit / 12.0)), 1) if gross_benefit > 0 else None

    return {
        "inputs": payload.model_dump(),
        "annual_inspections": annual_inspections,
        "savings": {
            "labor_usd": round(labor_saved_usd, 2),
            "reprocessing_usd": round(reprocessing_savings_usd, 2),
            "cancellation_avoidance_usd": round(cancellation_savings_usd, 2),
            "gross_benefit_usd": round(gross_benefit, 2),
        },
        "annual_cost_usd": round(cost, 2),
        "net_benefit_usd": round(net_benefit, 2),
        "roi_pct": roi_pct,
        "payback_months": payback_months,
        "assumptions": {
            "minutes_saved_per_inspection": MINUTES_SAVED_PER_INSPECTION,
            "staff_cost_per_hour_usd": STAFF_COST_PER_HOUR_USD,
            "reprocessing_cost_usd": REPROCESSING_COST_USD,
            "surgical_cancellation_cost_usd": SURGICAL_CANCELLATION_COST_USD,
            "reprocessing_capture_fraction": 0.60,
            "cancellation_capture_fraction": 0.01,
        },
        "human_review_required": True,
        "disclaimer": "ROI estimate for business-case modeling only. Not a guarantee. "
                      "Validate assumptions with your organization before contracting.",
    }


@router.get("/business-case/executive-summary")
def executive_business_case(
    tenant_id: str | None = Query(default=None),
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Generate an executive business-case summary combining adoption, quality,
    and modeled ROI. Audit-logged as a commercial artifact access."""
    insp_30 = _inspection_count(db, tenant_id, 30)
    annualized = insp_30 * 12

    start, _end = _date_range(30)
    cq = db.query(sqlfunc.count(models.Inspection.id)).filter(
        models.Inspection.created_at >= start,
        models.Inspection.stain_detected.is_(True),
    )
    if tenant_id:
        cq = cq.filter(models.Inspection.tenant_id == tenant_id)
    contamination = int(cq.scalar() or 0)
    contamination_rate = round((contamination / insp_30 * 100), 1) if insp_30 else 0.0

    minutes_saved = annualized * MINUTES_SAVED_PER_INSPECTION
    labor_usd = (minutes_saved / 60.0) * STAFF_COST_PER_HOUR_USD
    reprocessing_usd = (contamination * 12) * 0.60 * REPROCESSING_COST_USD
    gross_benefit = labor_usd + reprocessing_usd

    try:
        log_audit_event(
            db,
            tenant_id=tenant_id or "platform",
            tenant_name="Commercial",
            actor_email=getattr(current_user, "email", "unknown"),
            actor_role=getattr(current_user, "role", "executive"),
            action_type="commercial_business_case_view",
            resource_type="executive_business_case",
            details={"tenant_id": tenant_id},
            compliance_flag=True,
        )
    except Exception:
        pass

    return {
        "tenant_id": tenant_id,
        "period_days": 30,
        "adoption": {
            "inspections_last_30d": insp_30,
            "annualized_run_rate": annualized,
        },
        "quality": {
            "contamination_rate_pct": contamination_rate,
            "human_review_required": True,
            "note": "Candidate quality signal; not a clinical or regulatory determination.",
        },
        "modeled_annual_savings_usd": round(gross_benefit, 2),
        "rag": _rag(100 - contamination_rate, 95),
        "disclaimer": "Executive business case for internal modeling. No FDA clearance "
                      "or regulatory approval is claimed. All quality signals require human review.",
    }
