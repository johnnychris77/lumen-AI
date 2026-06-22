"""P16 Phases 4-6: Executive dashboards, adoption analytics, readiness scoring."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.db import models

router = APIRouter(prefix="/api/enterprise/dashboards", tags=["enterprise-dashboards"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_READINESS_WEIGHTS = {
    "training": 0.20,
    "adoption": 0.25,
    "baseline_coverage": 0.20,
    "inspection_volume": 0.20,
    "data_quality": 0.15,
}

_READINESS_THRESHOLDS = {
    "ready": 80.0,
    "conditional": 60.0,
}

_INSPECTION_VOLUME_TARGET = 25   # per week
_COMPLETENESS_TARGET = 95.0
_REVIEW_RATE_TARGET = 80.0


def _date_range(days: int):
    now = datetime.now(timezone.utc)
    return now - timedelta(days=days), now


def _rag(value: float, target: float) -> str:
    if value >= target:
        return "green"
    if value >= target * 0.80:
        return "amber"
    return "red"


def _facility_inspection_stats(db: Session, tenant_id: str, days: int) -> dict:
    start, _ = _date_range(days)
    rows = db.query(models.Inspection).filter(
        models.Inspection.tenant_id == tenant_id,
        models.Inspection.created_at >= start,
    ).all()
    total = len(rows)
    contamination = sum(1 for r in rows if r.stain_detected)
    reviewed = sum(1 for r in rows if r.status in ("reviewed", "closed"))
    complete = sum(1 for r in rows if (
        r.instrument_type not in ("unknown", "", None) and
        r.site_name not in ("default-site", "", None)
    ))
    return {
        "total": total,
        "contamination": contamination,
        "reviewed": reviewed,
        "complete": complete,
        "contamination_rate_pct": round(contamination / total * 100, 1) if total else 0.0,
        "review_rate_pct": round(reviewed / total * 100, 1) if total else 0.0,
        "completeness_pct": round(complete / total * 100, 1) if total else 0.0,
    }


# ---------------------------------------------------------------------------
# PHASE 4: Executive Dashboards
# ---------------------------------------------------------------------------

# --- System quality dashboard ---
@router.get("/system-quality/{system_id}")
def system_quality_dashboard(
    system_id: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """Aggregate quality metrics rolled up across all facilities in a health system."""
    facilities = db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.system_id == system_id,
        models.EnterpriseFacility.is_active == True,  # noqa: E712
    ).all()

    facility_stats = []
    system_totals = {"total": 0, "contamination": 0, "reviewed": 0, "complete": 0}

    for f in facilities:
        stats = _facility_inspection_stats(db, f.tenant_id, days)
        facility_stats.append({
            "facility_id": f.facility_id,
            "facility_name": f.facility_name,
            "market_id": f.market_id,
            "region_id": f.region_id,
            **stats,
        })
        for k in system_totals:
            system_totals[k] += stats[k]

    total = system_totals["total"]
    system_contamination_rate = round(system_totals["contamination"] / total * 100, 1) if total else 0.0
    system_review_rate = round(system_totals["reviewed"] / total * 100, 1) if total else 0.0
    system_completeness = round(system_totals["complete"] / total * 100, 1) if total else 0.0

    # Rollup KPIs
    kpis = [
        {"name": "System-wide inspections", "value": total, "unit": "inspections",
         "status": _rag(total, len(facilities) * _INSPECTION_VOLUME_TARGET * (days / 7))},
        {"name": "Contamination rate", "value": system_contamination_rate, "unit": "%",
         "status": "tracked"},
        {"name": "Review rate", "value": system_review_rate, "unit": "%",
         "status": _rag(system_review_rate, _REVIEW_RATE_TARGET)},
        {"name": "Data completeness", "value": system_completeness, "unit": "%",
         "status": _rag(system_completeness, _COMPLETENESS_TARGET)},
        {"name": "Active facilities", "value": len(facilities), "unit": "facilities",
         "status": "tracked"},
    ]

    # Identify outlier facilities (contamination > 2× system average)
    outliers = [f for f in facility_stats
                if total > 0 and f["contamination_rate_pct"] > system_contamination_rate * 2
                and f["total"] >= 5]

    log_audit_event(db, tenant_id=system_id, tenant_name="System Dashboard",
                    actor_email=getattr(current_user, "email", "unknown"),
                    actor_role=getattr(current_user, "role", "admin"),
                    action_type="system_quality_dashboard_accessed",
                    resource_type="enterprise_dashboard")

    return {
        "system_id": system_id,
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "facility_count": len(facilities),
        "kpis": kpis,
        "system_totals": system_totals,
        "facility_breakdown": facility_stats,
        "outlier_facilities": outliers,
        "human_review_required": True,
        "note": "Quality metrics are process indicators. Association does not imply causation.",
    }


# --- Market director dashboard ---
@router.get("/market/{market_id}")
def market_director_dashboard(
    market_id: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """Market-level rollup for market directors."""
    facilities = db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.market_id == market_id,
        models.EnterpriseFacility.is_active == True,  # noqa: E712
    ).all()

    market = db.query(models.EnterpriseMarket).filter(
        models.EnterpriseMarket.market_id == market_id
    ).first()

    facility_stats = []
    totals = {"total": 0, "contamination": 0, "reviewed": 0}

    for f in facilities:
        stats = _facility_inspection_stats(db, f.tenant_id, days)
        facility_stats.append({
            "facility_id": f.facility_id, "facility_name": f.facility_name, **stats
        })
        totals["total"] += stats["total"]
        totals["contamination"] += stats["contamination"]
        totals["reviewed"] += stats["reviewed"]

    # Onboarding status
    onboarding_counts = {"pending": 0, "in_progress": 0, "completed": 0}
    for f in facilities:
        status = f.onboarding_status
        if status in onboarding_counts:
            onboarding_counts[status] += 1

    # Baseline coverage
    if facilities:
        system_id = facilities[0].system_id
        approved_baselines = db.query(models.EnterpriseBaseline).filter(
            models.EnterpriseBaseline.system_id == system_id,
            models.EnterpriseBaseline.approval_status == "approved",
        ).count()
    else:
        approved_baselines = 0

    return {
        "market_id": market_id,
        "market_name": market.market_name if market else market_id,
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "facility_count": len(facilities),
        "totals": totals,
        "contamination_rate_pct": round(totals["contamination"] / totals["total"] * 100, 1) if totals["total"] else 0.0,
        "review_rate_pct": round(totals["reviewed"] / totals["total"] * 100, 1) if totals["total"] else 0.0,
        "onboarding_status": onboarding_counts,
        "approved_baselines": approved_baselines,
        "facility_breakdown": facility_stats,
        "human_review_required": True,
    }


# --- Enterprise executive scorecard ---
@router.get("/executive-scorecard/{system_id}")
def enterprise_executive_scorecard(
    system_id: str,
    days: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """Enterprise-wide executive scorecard across all facilities and markets."""
    hs = db.query(models.HealthSystem).filter(
        models.HealthSystem.system_id == system_id
    ).first()

    facilities = db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.system_id == system_id,
    ).all()
    active_facilities = [f for f in facilities if f.is_active]

    # Aggregate inspection stats
    all_stats = [_facility_inspection_stats(db, f.tenant_id, days) for f in active_facilities]
    total_inspections = sum(s["total"] for s in all_stats)
    total_contamination = sum(s["contamination"] for s in all_stats)
    total_reviewed = sum(s["reviewed"] for s in all_stats)
    total_complete = sum(s["complete"] for s in all_stats)

    # Onboarding
    onboarding_done = sum(1 for f in facilities if f.onboarding_status == "completed")
    onboarding_pct = round(onboarding_done / len(facilities) * 100) if facilities else 0.0

    # Baselines
    total_baselines = db.query(models.EnterpriseBaseline).filter(
        models.EnterpriseBaseline.system_id == system_id,
        models.EnterpriseBaseline.is_active == True,  # noqa: E712
    ).count()
    approved_baselines = db.query(models.EnterpriseBaseline).filter(
        models.EnterpriseBaseline.system_id == system_id,
        models.EnterpriseBaseline.approval_status == "approved",
    ).count()
    baseline_approval_pct = round(approved_baselines / total_baselines * 100) if total_baselines else 0.0

    review_rate = round(total_reviewed / total_inspections * 100, 1) if total_inspections else 0.0
    completeness = round(total_complete / total_inspections * 100, 1) if total_inspections else 0.0
    contamination_rate = round(total_contamination / total_inspections * 100, 1) if total_inspections else 0.0

    kpis = [
        {"name": "Active facilities", "value": len(active_facilities), "target": len(facilities),
         "unit": "facilities", "status": _rag(len(active_facilities), len(facilities))},
        {"name": "Facility onboarding completion", "value": onboarding_pct, "target": 100,
         "unit": "%", "status": _rag(onboarding_pct, 100)},
        {"name": "Total inspections", "value": total_inspections, "target": None,
         "unit": "inspections", "status": "tracked"},
        {"name": "Review rate", "value": review_rate, "target": _REVIEW_RATE_TARGET,
         "unit": "%", "status": _rag(review_rate, _REVIEW_RATE_TARGET)},
        {"name": "Data completeness", "value": completeness, "target": _COMPLETENESS_TARGET,
         "unit": "%", "status": _rag(completeness, _COMPLETENESS_TARGET)},
        {"name": "Baseline approval rate", "value": baseline_approval_pct, "target": 80,
         "unit": "%", "status": _rag(baseline_approval_pct, 80)},
        {"name": "Contamination rate", "value": contamination_rate, "target": None,
         "unit": "%", "status": "tracked"},
    ]

    rag_kpis = [k for k in kpis if k["target"] is not None]
    red = sum(1 for k in rag_kpis if k["status"] == "red")
    amber = sum(1 for k in rag_kpis if k["status"] == "amber")
    overall = "green" if red == 0 and amber <= 1 else ("amber" if red <= 1 else "red")

    log_audit_event(db, tenant_id=system_id, tenant_name="Enterprise Scorecard",
                    actor_email=getattr(current_user, "email", "unknown"),
                    actor_role=getattr(current_user, "role", "admin"),
                    action_type="enterprise_scorecard_accessed",
                    resource_type="enterprise_dashboard", compliance_flag=True)

    return {
        "system_id": system_id,
        "system_name": hs.system_name if hs else system_id,
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "kpis": kpis,
        "summary": {"green": sum(1 for k in rag_kpis if k["status"] == "green"),
                    "amber": amber, "red": red},
        "human_review_required": True,
        "disclaimer": "Enterprise scorecard values are quality process indicators. Requires human review.",
    }


# --- Enterprise benchmarking dashboard ---
@router.get("/benchmarking/{system_id}")
def enterprise_benchmarking(
    system_id: str,
    days: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """Anonymised peer benchmarking across facilities within the health system."""
    facilities = db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.system_id == system_id,
        models.EnterpriseFacility.is_active == True,  # noqa: E712
    ).all()

    facility_metrics = []
    for f in facilities:
        stats = _facility_inspection_stats(db, f.tenant_id, days)
        facility_metrics.append({
            "facility_id": f.facility_id,
            "facility_name": f.facility_name,
            "total": stats["total"],
            "contamination_rate_pct": stats["contamination_rate_pct"],
            "completeness_pct": stats["completeness_pct"],
            "review_rate_pct": stats["review_rate_pct"],
        })

    # Compute system averages
    n = len(facility_metrics)
    if n:
        avg_contamination = round(sum(f["contamination_rate_pct"] for f in facility_metrics) / n, 2)
        avg_completeness = round(sum(f["completeness_pct"] for f in facility_metrics) / n, 2)
        avg_review_rate = round(sum(f["review_rate_pct"] for f in facility_metrics) / n, 2)
        avg_volume = round(sum(f["total"] for f in facility_metrics) / n, 1)
    else:
        avg_contamination = avg_completeness = avg_review_rate = avg_volume = 0.0

    # Rank facilities
    for f in facility_metrics:
        f["vs_system_avg_contamination"] = round(f["contamination_rate_pct"] - avg_contamination, 2)
        f["vs_system_avg_completeness"] = round(f["completeness_pct"] - avg_completeness, 2)
        f["quartile_volume"] = (
            "top" if f["total"] >= avg_volume * 1.25 else
            "bottom" if f["total"] < avg_volume * 0.75 else "mid"
        )

    return {
        "system_id": system_id,
        "period_days": days,
        "facility_count": n,
        "system_averages": {
            "contamination_rate_pct": avg_contamination,
            "completeness_pct": avg_completeness,
            "review_rate_pct": avg_review_rate,
            "inspection_volume": avg_volume,
        },
        "external_benchmarks": {
            "contamination_rate_pct": 2.0,
            "completeness_pct": 95.0,
            "source": "AAMI ST79 / IAHCSMM (indicative)",
        },
        "facility_metrics": sorted(facility_metrics, key=lambda x: x["contamination_rate_pct"], reverse=True),
        "human_review_required": True,
        "note": "Benchmarking data is for quality improvement purposes only. Association does not imply causation.",
    }


# ---------------------------------------------------------------------------
# PHASE 5: Adoption Analytics
# ---------------------------------------------------------------------------

@router.get("/adoption/{system_id}")
def enterprise_adoption_analytics(
    system_id: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """Track active users, inspections, baseline reviews, and adoption rates across facilities."""
    facilities = db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.system_id == system_id,
        models.EnterpriseFacility.is_active == True,  # noqa: E712
    ).all()

    start, end = _date_range(days)

    facility_adoption = []
    system_inspection_total = 0
    active_facility_count = 0

    for f in facilities:
        stats = _facility_inspection_stats(db, f.tenant_id, days)
        vol = stats["total"]
        system_inspection_total += vol
        is_active_facility = vol > 0
        if is_active_facility:
            active_facility_count += 1

        # Baseline coverage: distinct instrument types with approved baselines
        baselines_for_facility = db.query(models.EnterpriseBaseline).filter(
            models.EnterpriseBaseline.system_id == system_id,
            models.EnterpriseBaseline.approval_status == "approved",
        ).all()
        instrument_types_covered = {b.instrument_type for b in baselines_for_facility}
        inspected_types = set()
        if vol > 0:
            rows = db.query(models.Inspection).filter(
                models.Inspection.tenant_id == f.tenant_id,
                models.Inspection.created_at >= start,
            ).all()
            inspected_types = {r.instrument_type for r in rows if r.instrument_type not in ("unknown", "")}

        coverage_pct = round(
            len(inspected_types & instrument_types_covered) / len(inspected_types) * 100
        ) if inspected_types else 0.0

        # Weekly trend (4 weeks)
        weekly_trend = []
        for w in range(4):
            w_end = end - timedelta(weeks=w)
            w_start = w_end - timedelta(weeks=1)
            count = db.query(sqlfunc.count(models.Inspection.id)).filter(
                models.Inspection.tenant_id == f.tenant_id,
                models.Inspection.created_at >= w_start,
                models.Inspection.created_at < w_end,
            ).scalar() or 0
            weekly_trend.append({"week_ending": w_end.strftime("%Y-%m-%d"), "count": count})

        facility_adoption.append({
            "facility_id": f.facility_id,
            "facility_name": f.facility_name,
            "inspection_volume": vol,
            "is_active": is_active_facility,
            "review_rate_pct": stats["review_rate_pct"],
            "completeness_pct": stats["completeness_pct"],
            "baseline_coverage_pct": coverage_pct,
            "weekly_trend": list(reversed(weekly_trend)),
        })

    utilization_rate = round(active_facility_count / len(facilities) * 100) if facilities else 0.0

    # Onboarding pipeline
    wf_totals = {"in_progress": 0, "completed": 0, "pending": 0}
    workflows = db.query(models.OnboardingWorkflow).filter(
        models.OnboardingWorkflow.system_id == system_id
    ).all()
    for wf in workflows:
        if wf.status in wf_totals:
            wf_totals[wf.status] += 1

    return {
        "system_id": system_id,
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_summary": {
            "total_facilities": len(facilities),
            "active_facilities": active_facility_count,
            "facility_utilization_rate_pct": utilization_rate,
            "total_inspections": system_inspection_total,
            "inspections_per_facility_avg": round(system_inspection_total / len(facilities), 1) if facilities else 0.0,
        },
        "onboarding_pipeline": wf_totals,
        "facility_adoption": sorted(facility_adoption, key=lambda x: x["inspection_volume"], reverse=True),
        "human_review_required": True,
    }


# ---------------------------------------------------------------------------
# PHASE 6: Facility Readiness Scoring
# ---------------------------------------------------------------------------

def _compute_readiness(
    facility: models.EnterpriseFacility,
    stats: dict,
    baseline_coverage_pct: float,
    has_completed_onboarding: bool,
    days: int,
) -> dict:
    """Score a facility on 5 dimensions (0–100 each) and compute weighted overall."""
    # Training (proxy: onboarding completion + review rate)
    training_score = 100.0 if has_completed_onboarding else (
        50.0 if facility.onboarding_status == "in_progress" else 10.0
    )

    # Adoption: weekly volume vs. target
    weekly_target = _INSPECTION_VOLUME_TARGET * (days / 7)
    adoption_score = min(100.0, round(stats["total"] / max(weekly_target, 1) * 100, 1))

    # Baseline coverage
    baseline_coverage_score = min(100.0, baseline_coverage_pct)

    # Inspection volume (same as adoption for simplicity — different KPI framing)
    inspection_volume_score = min(100.0, round(stats["total"] / max(weekly_target, 1) * 100, 1))

    # Data quality: completeness
    data_quality_score = stats["completeness_pct"]

    overall = round(
        training_score * _READINESS_WEIGHTS["training"] +
        adoption_score * _READINESS_WEIGHTS["adoption"] +
        baseline_coverage_score * _READINESS_WEIGHTS["baseline_coverage"] +
        inspection_volume_score * _READINESS_WEIGHTS["inspection_volume"] +
        data_quality_score * _READINESS_WEIGHTS["data_quality"],
        1,
    )

    status = (
        "ready" if overall >= _READINESS_THRESHOLDS["ready"] else
        "conditional" if overall >= _READINESS_THRESHOLDS["conditional"] else
        "not_ready"
    )

    return {
        "training_score": round(training_score, 1),
        "adoption_score": round(adoption_score, 1),
        "baseline_coverage_score": round(baseline_coverage_score, 1),
        "inspection_volume_score": round(inspection_volume_score, 1),
        "data_quality_score": round(data_quality_score, 1),
        "overall_score": overall,
        "readiness_status": status,
    }


@router.get("/readiness/{system_id}")
def system_readiness_scores(
    system_id: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """Compute facility readiness scores for enterprise expansion decisions."""
    facilities = db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.system_id == system_id,
        models.EnterpriseFacility.is_active == True,  # noqa: E712
    ).all()

    approved_baselines = db.query(models.EnterpriseBaseline).filter(
        models.EnterpriseBaseline.system_id == system_id,
        models.EnterpriseBaseline.approval_status == "approved",
    ).all()
    covered_instrument_types = {b.instrument_type for b in approved_baselines}

    readiness_results = []
    for f in facilities:
        stats = _facility_inspection_stats(db, f.tenant_id, days)

        # Baseline coverage for this facility
        start, _ = _date_range(days)
        inspected_types: set = set()
        if stats["total"] > 0:
            rows = db.query(models.Inspection).filter(
                models.Inspection.tenant_id == f.tenant_id,
                models.Inspection.created_at >= start,
            ).all()
            inspected_types = {r.instrument_type for r in rows if r.instrument_type not in ("unknown", "")}

        baseline_coverage_pct = round(
            len(inspected_types & covered_instrument_types) / len(inspected_types) * 100
        ) if inspected_types else 0.0

        completed_wf = db.query(models.OnboardingWorkflow).filter(
            models.OnboardingWorkflow.facility_id == f.facility_id,
            models.OnboardingWorkflow.workflow_type == "site",
            models.OnboardingWorkflow.status == "completed",
        ).first()

        scores = _compute_readiness(
            facility=f, stats=stats,
            baseline_coverage_pct=baseline_coverage_pct,
            has_completed_onboarding=completed_wf is not None,
            days=days,
        )

        # Persist readiness snapshot
        snap = models.FacilityReadinessScore(
            facility_id=f.facility_id, system_id=system_id, **scores
        )
        db.add(snap)

        readiness_results.append({
            "facility_id": f.facility_id, "facility_name": f.facility_name,
            "market_id": f.market_id, "region_id": f.region_id,
            **scores,
            "inspection_count": stats["total"],
        })

    try:
        db.commit()
    except Exception:
        db.rollback()

    ready = [r for r in readiness_results if r["readiness_status"] == "ready"]
    conditional = [r for r in readiness_results if r["readiness_status"] == "conditional"]
    not_ready = [r for r in readiness_results if r["readiness_status"] == "not_ready"]

    return {
        "system_id": system_id,
        "period_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "facility_count": len(facilities),
        "summary": {
            "ready": len(ready),
            "conditional": len(conditional),
            "not_ready": len(not_ready),
        },
        "readiness_scores": sorted(readiness_results, key=lambda x: x["overall_score"], reverse=True),
        "expansion_candidate_facilities": [r["facility_id"] for r in ready],
        "weights_used": _READINESS_WEIGHTS,
        "thresholds": _READINESS_THRESHOLDS,
        "human_review_required": True,
        "note": "Readiness scores are advisory indicators. Expansion decisions require clinical and operational leadership review.",
    }


@router.get("/readiness/{system_id}/facility/{facility_id}")
def facility_readiness_detail(
    system_id: str,
    facility_id: str,
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    """Detailed readiness breakdown with gap analysis for a single facility."""
    f = db.query(models.EnterpriseFacility).filter(
        models.EnterpriseFacility.facility_id == facility_id,
        models.EnterpriseFacility.system_id == system_id,
    ).first()
    if not f:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Facility not found")

    stats = _facility_inspection_stats(db, f.tenant_id, days)

    approved_baselines = db.query(models.EnterpriseBaseline).filter(
        models.EnterpriseBaseline.system_id == system_id,
        models.EnterpriseBaseline.approval_status == "approved",
    ).all()
    covered_instrument_types = {b.instrument_type for b in approved_baselines}

    start, _ = _date_range(days)
    inspected_types: set = set()
    if stats["total"] > 0:
        rows = db.query(models.Inspection).filter(
            models.Inspection.tenant_id == f.tenant_id,
            models.Inspection.created_at >= start,
        ).all()
        inspected_types = {r.instrument_type for r in rows if r.instrument_type not in ("unknown", "")}

    baseline_coverage_pct = round(
        len(inspected_types & covered_instrument_types) / len(inspected_types) * 100
    ) if inspected_types else 0.0

    completed_wf = db.query(models.OnboardingWorkflow).filter(
        models.OnboardingWorkflow.facility_id == facility_id,
        models.OnboardingWorkflow.workflow_type == "site",
        models.OnboardingWorkflow.status == "completed",
    ).first()

    scores = _compute_readiness(
        facility=f, stats=stats,
        baseline_coverage_pct=baseline_coverage_pct,
        has_completed_onboarding=completed_wf is not None,
        days=days,
    )

    # Gap analysis
    gaps = []
    if scores["training_score"] < 80:
        gaps.append({"dimension": "training", "score": scores["training_score"],
                     "action": "Complete site onboarding workflow and staff training"})
    if scores["adoption_score"] < 80:
        gaps.append({"dimension": "adoption", "score": scores["adoption_score"],
                     "action": f"Increase weekly inspection volume toward {_INSPECTION_VOLUME_TARGET}/week target"})
    if scores["baseline_coverage_score"] < 80:
        gaps.append({"dimension": "baseline_coverage", "score": scores["baseline_coverage_score"],
                     "action": "Request enterprise baseline distribution for uncovered instrument types"})
    if scores["data_quality_score"] < 80:
        gaps.append({"dimension": "data_quality", "score": scores["data_quality_score"],
                     "action": "Review data entry training — completeness below 80%"})

    return {
        "facility_id": facility_id,
        "facility_name": f.facility_name,
        "system_id": system_id,
        **scores,
        "gap_analysis": gaps,
        "inspection_stats": stats,
        "baseline_coverage_pct": baseline_coverage_pct,
        "onboarding_complete": completed_wf is not None,
        "human_review_required": True,
    }
