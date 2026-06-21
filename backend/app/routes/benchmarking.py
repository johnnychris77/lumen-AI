"""P5: Enterprise Multi-Hospital Benchmarking & Portfolio Intelligence API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.deps import get_db
from app.enterprise_auth import require_enterprise_auth
from app.schemas.benchmarking import (
    BoardReportRequest,
    BoardReportResult,
    EnterpriseRollupRequest,
    EnterpriseRollupResult,
    ExecutiveDashboard,
    HospitalBenchmarkRequest,
    HospitalBenchmarkResult,
    TrendSeries,
    VendorBenchmarkRequest,
    VendorBenchmarkResult,
)
from app.services.benchmark_engine import (
    _current_period_label,
    compute_enterprise_rollup,
    compute_executive_dashboard,
    compute_hospital_benchmarks,
    compute_trend_series,
    compute_vendor_benchmarks,
    generate_board_report,
)

router = APIRouter(prefix="/api/enterprise/benchmarks", tags=["benchmarking"])


# ── Hospital benchmarking ─────────────────────────────────────────────────────

@router.post("/hospitals", response_model=list[HospitalBenchmarkResult])
def hospital_benchmarks(
    req: HospitalBenchmarkRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Compute and return benchmark metrics for each hospital in the portfolio.

    Aggregates CVInferenceRecord data for the specified period.
    Pass hospital_ids=[] to include all hospitals.
    """
    require_enterprise_auth(request)
    period_label = req.period.period_label or _current_period_label(req.period.period_type)
    return compute_hospital_benchmarks(
        tenant_id=req.tenant_id,
        period_label=period_label,
        period_type=req.period.period_type,
        hospital_ids=req.hospital_ids or None,
        db=db,
    )


@router.get("/hospitals/{hospital_id}", response_model=HospitalBenchmarkResult)
def get_hospital_benchmark(
    hospital_id: str,
    request: Request,
    tenant_id: str = "demo-tenant",
    period_label: str = "",
    period_type: str = "monthly",
    db: Session = Depends(get_db),
):
    """Retrieve benchmark for a single hospital."""
    require_enterprise_auth(request)
    period_label = period_label or _current_period_label(period_type)
    results = compute_hospital_benchmarks(
        tenant_id=tenant_id,
        period_label=period_label,
        period_type=period_type,
        hospital_ids=[hospital_id],
        db=db,
    )
    # Return first match or a zeroed-out placeholder
    for r in results:
        if r.hospital_id == hospital_id:
            return r
    return HospitalBenchmarkResult(
        hospital_id=hospital_id,
        hospital_name=hospital_id,
        period_label=period_label,
    )


@router.get("/hospitals", response_model=list[HospitalBenchmarkResult])
def list_hospital_benchmarks(
    request: Request,
    tenant_id: str = "demo-tenant",
    period_label: str = "",
    period_type: str = "monthly",
    db: Session = Depends(get_db),
):
    """List all hospital benchmarks for the current period (GET shorthand)."""
    require_enterprise_auth(request)
    period_label = period_label or _current_period_label(period_type)
    return compute_hospital_benchmarks(
        tenant_id=tenant_id,
        period_label=period_label,
        period_type=period_type,
        db=db,
    )


# ── Vendor benchmarking ───────────────────────────────────────────────────────

@router.post("/vendors", response_model=list[VendorBenchmarkResult])
def vendor_benchmarks(
    req: VendorBenchmarkRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Compute vendor benchmark metrics: baseline adoption, defect rate, CAPA closure."""
    require_enterprise_auth(request)
    period_label = req.period.period_label or _current_period_label(req.period.period_type)
    return compute_vendor_benchmarks(
        tenant_id=req.tenant_id,
        period_label=period_label,
        period_type=req.period.period_type,
        vendor_ids=req.vendor_ids or None,
        db=db,
    )


@router.get("/vendors", response_model=list[VendorBenchmarkResult])
def list_vendor_benchmarks(
    request: Request,
    tenant_id: str = "demo-tenant",
    period_label: str = "",
    period_type: str = "monthly",
    db: Session = Depends(get_db),
):
    """List all vendor benchmarks for the current period."""
    require_enterprise_auth(request)
    period_label = period_label or _current_period_label(period_type)
    return compute_vendor_benchmarks(
        tenant_id=tenant_id,
        period_label=period_label,
        period_type=period_type,
        db=db,
    )


# ── Enterprise rollup ─────────────────────────────────────────────────────────

@router.post("/rollup", response_model=EnterpriseRollupResult)
def enterprise_rollup(
    req: EnterpriseRollupRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Cross-hospital enterprise rollup for the specified period.

    Aggregates all hospital and vendor benchmarks into a single summary
    suitable for executive reporting.
    """
    require_enterprise_auth(request)
    period_label = req.period.period_label or _current_period_label(req.period.period_type)
    return compute_enterprise_rollup(
        tenant_id=req.tenant_id,
        period_label=period_label,
        period_type=req.period.period_type,
        db=db,
    )


@router.get("/rollup", response_model=EnterpriseRollupResult)
def get_enterprise_rollup(
    request: Request,
    tenant_id: str = "demo-tenant",
    period_label: str = "",
    period_type: str = "monthly",
    db: Session = Depends(get_db),
):
    """GET shorthand for the current-period enterprise rollup."""
    require_enterprise_auth(request)
    period_label = period_label or _current_period_label(period_type)
    return compute_enterprise_rollup(
        tenant_id=tenant_id,
        period_label=period_label,
        period_type=period_type,
        db=db,
    )


# ── Executive dashboard ───────────────────────────────────────────────────────

@router.get("/executive-dashboard", response_model=ExecutiveDashboard)
def executive_dashboard(
    request: Request,
    tenant_id: str = "demo-tenant",
    period_label: str = "",
    period_type: str = "monthly",
    db: Session = Depends(get_db),
):
    """Single-payload executive dashboard for C-suite, Market Directors, SPD Directors,
    and Quality Leaders.

    Includes headline KPIs, trend series for the last 6 periods, risk snapshot,
    leaderboards, and role-specific insights.
    """
    require_enterprise_auth(request)
    period_label = period_label or _current_period_label(period_type)
    return compute_executive_dashboard(
        tenant_id=tenant_id,
        period_label=period_label,
        period_type=period_type,
        db=db,
    )


# ── Trend series ──────────────────────────────────────────────────────────────

@router.get("/trends/{subject_type}/{subject_id}/{metric_name}", response_model=TrendSeries)
def metric_trend(
    subject_type: str,
    subject_id: str,
    metric_name: str,
    request: Request,
    tenant_id: str = "demo-tenant",
    n_periods: int = 6,
    period_type: str = "monthly",
    db: Session = Depends(get_db),
):
    """Time-series trend for a specific metric on a hospital, vendor, or enterprise.

    subject_type: hospital | vendor | enterprise
    metric_name:  contamination_rate_pct | avg_cleanliness_score | baseline_adoption_rate_pct | etc.
    """
    require_enterprise_auth(request)
    n_periods = max(2, min(n_periods, 24))
    points = compute_trend_series(
        tenant_id=tenant_id,
        subject_type=subject_type,
        subject_id=subject_id,
        metric_name=metric_name,
        n_periods=n_periods,
        period_type=period_type,
        db=db,
    )
    return TrendSeries(
        subject_id=subject_id,
        subject_name=subject_id.replace("-", " ").title(),
        metric_name=metric_name,
        points=points,
    )


# ── Board reporting ───────────────────────────────────────────────────────────

@router.post("/reports/generate", response_model=BoardReportResult)
def generate_report(
    req: BoardReportRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Generate a monthly, quarterly, or annual benchmark board report.

    The report includes an executive summary, key findings, and recommendations
    derived from the enterprise rollup for the specified period.
    Set publish=True to mark the report as published.
    """
    require_enterprise_auth(request)
    period_label = req.period_label or _current_period_label(req.report_type)
    period_type = req.report_type
    report = generate_board_report(
        tenant_id=req.tenant_id,
        period_label=period_label,
        period_type=period_type,
        report_type=req.report_type,
        db=db,
    )
    if req.publish and db is not None:
        _publish_report(db, req.tenant_id, period_label, req.report_type)
        report = report.model_copy(update={"status": "published"})
    return report


@router.get("/reports/{report_type}", response_model=list[dict])
def list_reports(
    report_type: str,
    request: Request,
    tenant_id: str = "demo-tenant",
    db: Session = Depends(get_db),
):
    """List previously generated board reports of the specified type."""
    from app.models.benchmarking import BoardReport
    require_enterprise_auth(request)
    import json as _json
    rows = (
        db.query(BoardReport)
        .filter(
            BoardReport.tenant_id == tenant_id,
            BoardReport.report_type == report_type,
        )
        .order_by(BoardReport.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "period_label": r.period_label,
            "status": r.status,
            "key_findings_count": len(_json.loads(r.key_findings_json or "[]")),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/reports/{report_type}/{period_label}", response_model=BoardReportResult)
def get_report(
    report_type: str,
    period_label: str,
    request: Request,
    tenant_id: str = "demo-tenant",
    db: Session = Depends(get_db),
):
    """Retrieve a specific board report by type and period."""
    from app.models.benchmarking import BoardReport
    import json as _json
    require_enterprise_auth(request)
    row = (
        db.query(BoardReport)
        .filter(
            BoardReport.tenant_id == tenant_id,
            BoardReport.report_type == report_type,
            BoardReport.period_label == period_label,
        )
        .first()
    )
    if row:
        return BoardReportResult(
            id=row.id,
            tenant_id=tenant_id,
            report_type=row.report_type,
            period_label=row.period_label,
            title=row.title,
            executive_summary=row.executive_summary,
            key_findings=_json.loads(row.key_findings_json or "[]"),
            recommendations=_json.loads(row.recommendations_json or "[]"),
            status=row.status,
            generated_by=row.generated_by,
            published_at=row.published_at,
            created_at=row.created_at,
        )
    # Generate on-demand if not yet persisted
    return generate_board_report(
        tenant_id=tenant_id,
        period_label=period_label,
        period_type=report_type,
        report_type=report_type,
        db=db,
    )


# ── Portfolio KPI summary (dashboard card) ────────────────────────────────────

@router.get("/kpi-summary", response_model=dict)
def benchmark_kpi_summary(
    request: Request,
    tenant_id: str = "demo-tenant",
    period_type: str = "monthly",
    db: Session = Depends(get_db),
):
    """Lightweight KPI summary suitable for dashboard tiles.

    Returns the most important headline numbers without the full trend series.
    """
    require_enterprise_auth(request)
    period_label = _current_period_label(period_type)
    rollup = compute_enterprise_rollup(
        tenant_id=tenant_id,
        period_label=period_label,
        period_type=period_type,
        db=db,
    )
    return {
        "period_label": period_label,
        "total_hospitals": rollup.total_hospitals,
        "total_inspections": rollup.total_inspections,
        "portfolio_cleanliness_score": rollup.avg_cleanliness_score,
        "contamination_rate_pct": rollup.avg_contamination_rate_pct,
        "baseline_adoption_rate_pct": rollup.baseline_adoption_rate_pct,
        "pct_hospitals_compliant": rollup.pct_hospitals_compliant,
        "blood_findings": rollup.total_blood_findings,
        "hospitals_critical_risk": rollup.hospitals_critical_risk,
        "hospitals_high_risk": rollup.hospitals_high_risk,
        "top_hospital": rollup.top_hospitals[0] if rollup.top_hospitals else None,
        "top_vendor": rollup.top_vendors[0] if rollup.top_vendors else None,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _publish_report(db: Any, tenant_id: str, period_label: str, report_type: str) -> None:
    from app.models.benchmarking import BoardReport
    from datetime import datetime, timezone
    row = (
        db.query(BoardReport)
        .filter(
            BoardReport.tenant_id == tenant_id,
            BoardReport.period_label == period_label,
            BoardReport.report_type == report_type,
        )
        .first()
    )
    if row:
        row.status = "published"
        row.published_at = datetime.now(timezone.utc)
        db.commit()
