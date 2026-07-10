"""v3.4 — Project Horizon, Section 5: Global Benchmarking.

Reuses `network_benchmark_service.py`'s (P15) exact percentile-band +
Laplace-noise pattern — `_add_laplace_noise`, `MIN_FACILITIES = 5`
imported directly, never a second percentile engine — for six new metric
names P15 doesn't compute. Every percentile is computed from real
per-tenant values among enrolled organizations
(`horizon_participation_service.list_enrolled_tenant_ids`), never a
seeded-random mock. Callers are shown a percentile band
(`below_p25`/`p25_to_p50`/`p50_to_p75`/`p75_to_p90`/`above_p90`), never
another organization's raw value.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.digital_twin import InstrumentFlowRecord
from app.models.federated_horizon import BENCHMARK_METRICS
from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.knowledge import APPROVED, KnowledgeArticle
from app.models.or_connect import RepairRequest
from app.services import horizon_participation_service
from app.services.network_benchmark_service import MIN_FACILITIES, _add_laplace_noise

_LOOKBACK_DAYS = 90
_KERRISON_INSTRUMENT_TYPE = "kerrison_rongeur"


def _percentile_bands(values: list[float]) -> dict:
    values = sorted(values)
    n = len(values)
    return {
        "p25": round(_add_laplace_noise(values[int(0.25 * n)]), 4),
        "p50": round(_add_laplace_noise(values[int(0.50 * n)]), 4),
        "p75": round(_add_laplace_noise(values[int(0.75 * n)]), 4),
        "p90": round(_add_laplace_noise(values[min(n - 1, int(0.90 * n))]), 4),
        "mean": round(_add_laplace_noise(sum(values) / n), 4),
    }


def _per_tenant_values(db: Session, metric_name: str) -> dict[str, float]:
    """Returns {tenant_id: value} for enrolled tenants that have data for
    this metric — never fabricated for a tenant with no activity."""
    tenant_ids = horizon_participation_service.list_enrolled_tenant_ids(db)
    if not tenant_ids:
        return {}
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    values: dict[str, float] = {}

    if metric_name == "kerrison_blood_finding_rate":
        for tenant_id in tenant_ids:
            inspections = db.query(Inspection.id).filter(
                Inspection.tenant_id == tenant_id, Inspection.instrument_type == _KERRISON_INSTRUMENT_TYPE, Inspection.created_at >= since,
            ).all()
            if not inspections:
                continue
            insp_ids = [i[0] for i in inspections]
            blood_count = db.query(InspectionFinding.id).filter(
                InspectionFinding.inspection_id.in_(insp_ids), InspectionFinding.finding_type == "blood",
            ).count()
            values[tenant_id] = round(blood_count / len(insp_ids), 4)

    elif metric_name == "corrosion_trend":
        for tenant_id in tenant_ids:
            count = db.query(InspectionFinding.id).filter(
                InspectionFinding.tenant_id == tenant_id, InspectionFinding.finding_type == "corrosion", InspectionFinding.created_at >= since,
            ).count()
            total = db.query(Inspection.id).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since).count()
            if total:
                values[tenant_id] = round(count / total, 4)

    elif metric_name == "coverage_trend":
        for tenant_id in tenant_ids:
            rows = db.query(Inspection.coverage_pct).filter(
                Inspection.tenant_id == tenant_id, Inspection.created_at >= since, Inspection.coverage_pct.isnot(None),
            ).all()
            if rows:
                values[tenant_id] = round(sum(r[0] for r in rows) / len(rows), 2)

    elif metric_name == "repair_referral_rate":
        for tenant_id in tenant_ids:
            total = db.query(Inspection.id).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since).count()
            if not total:
                continue
            repairs = db.query(RepairRequest.id).filter(RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= since).count()
            values[tenant_id] = round(repairs / total, 4)

    elif metric_name == "knowledge_maturity_index":
        for tenant_id in tenant_ids:
            total = db.query(KnowledgeArticle.id).filter(KnowledgeArticle.tenant_id == tenant_id).count()
            if not total:
                continue
            approved = db.query(KnowledgeArticle.id).filter(KnowledgeArticle.tenant_id == tenant_id, KnowledgeArticle.approval_status == APPROVED).count()
            values[tenant_id] = round(approved / total, 4)

    elif metric_name == "training_maturity_index":
        from app.services.competency_service import technician_quality_dashboard
        for tenant_id in tenant_ids:
            dashboard = technician_quality_dashboard(db, tenant_id)
            progress_values = [t["training_progress_pct"] for t in dashboard.get("technicians", []) if t.get("training_progress_pct") is not None]
            if progress_values:
                values[tenant_id] = round(sum(progress_values) / len(progress_values), 2)

    elif metric_name == "repair_category_rate":
        # Added for Project Beacon (v3.5) Section 8 — share of a tenant's
        # repairs in the last _LOOKBACK_DAYS that carry a structured
        # `failure_category` at all (vs. only free-text `repair_type`),
        # a real signal of how well a tenant's repair data is categorized.
        for tenant_id in tenant_ids:
            total = db.query(RepairRequest.id).filter(
                RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= since,
            ).count()
            if not total:
                continue
            categorized = db.query(RepairRequest.id).filter(
                RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= since,
                RepairRequest.failure_category.isnot(None),
            ).count()
            values[tenant_id] = round(categorized / total, 4)

    elif metric_name == "digital_twin_health_score":
        # Added for Project Beacon (v3.5) Section 8 — share of a tenant's
        # instrument flow records in the last _LOOKBACK_DAYS with a
        # non-adverse outcome ("passed"), a real Digital Twin health signal.
        for tenant_id in tenant_ids:
            total = db.query(InstrumentFlowRecord.id).filter(
                InstrumentFlowRecord.tenant_id == tenant_id, InstrumentFlowRecord.arrived_at >= since,
            ).count()
            if not total:
                continue
            passed = db.query(InstrumentFlowRecord.id).filter(
                InstrumentFlowRecord.tenant_id == tenant_id, InstrumentFlowRecord.arrived_at >= since,
                InstrumentFlowRecord.outcome == "passed",
            ).count()
            values[tenant_id] = round(passed / total, 4)

    else:
        raise ValueError(f"metric_name must be one of {BENCHMARK_METRICS}")

    return values


def compute_horizon_benchmark(db: Session, metric_name: str) -> dict:
    if metric_name not in BENCHMARK_METRICS:
        raise ValueError(f"metric_name must be one of {BENCHMARK_METRICS}")

    per_tenant = _per_tenant_values(db, metric_name)
    n = len(per_tenant)
    suppressed = n < MIN_FACILITIES

    result = {"metric_name": metric_name, "n_facilities": n, "suppressed": suppressed, "noise_added": not suppressed}
    if suppressed:
        result.update({"p25": None, "p50": None, "p75": None, "p90": None, "mean": None})
    else:
        result.update(_percentile_bands(list(per_tenant.values())))
    return result


def compute_all_horizon_benchmarks(db: Session) -> list[dict]:
    return [compute_horizon_benchmark(db, m) for m in BENCHMARK_METRICS]


def get_tenant_benchmark_percentile(db: Session, tenant_id: str, metric_name: str) -> dict:
    if metric_name not in BENCHMARK_METRICS:
        raise ValueError(f"metric_name must be one of {BENCHMARK_METRICS}")

    per_tenant = _per_tenant_values(db, metric_name)
    if tenant_id not in per_tenant:
        return {"metric_name": metric_name, "percentile_band": None, "suppressed": True, "reason": "no_activity_for_tenant"}

    benchmark = compute_horizon_benchmark(db, metric_name)
    if benchmark["suppressed"]:
        return {"metric_name": metric_name, "percentile_band": None, "suppressed": True, "reason": "insufficient_participants"}

    tenant_value = per_tenant[tenant_id]
    p25, p50, p75, p90 = benchmark["p25"], benchmark["p50"], benchmark["p75"], benchmark["p90"]
    if tenant_value < p25:
        band = "below_p25"
    elif tenant_value < p50:
        band = "p25_to_p50"
    elif tenant_value < p75:
        band = "p50_to_p75"
    elif tenant_value < p90:
        band = "p75_to_p90"
    else:
        band = "above_p90"

    return {"metric_name": metric_name, "percentile_band": band, "network_p50": p50, "suppressed": False}
