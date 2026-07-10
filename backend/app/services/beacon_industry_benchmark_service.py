"""v3.5 — Project Beacon, Section 8: Industry Benchmarking.

Reuses `horizon_benchmark_service.py` / `federated_horizon.py::
BENCHMARK_METRICS` directly rather than a sixth percentile engine.
`BENCHMARK_METRICS` was extended with `repair_category_rate` and
`digital_twin_health_score` for this section; every other metric
(instrument family / manufacturer signal via `kerrison_blood_finding_rate`
and `corrosion_trend`, repair category via `repair_category_rate`,
inspection quality via `coverage_trend`, education effectiveness via
`training_maturity_index`, Digital Twin health via
`digital_twin_health_score`) already existed. "Display percentile
rankings only" is exactly what `get_tenant_benchmark_percentile` already
guarantees — this module adds no new raw-value exposure.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.federated_horizon import BENCHMARK_METRICS, DISCLAIMER
from app.services import horizon_benchmark_service


def industry_benchmarks(db: Session) -> dict:
    return {
        "benchmarks": horizon_benchmark_service.compute_all_horizon_benchmarks(db),
        "metrics": BENCHMARK_METRICS,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def tenant_percentile(db: Session, tenant_id: str, metric_name: str) -> dict:
    if metric_name not in BENCHMARK_METRICS:
        raise ValueError(f"metric_name must be one of {BENCHMARK_METRICS}")
    return horizon_benchmark_service.get_tenant_benchmark_percentile(db, tenant_id, metric_name)


def tenant_percentile_all(db: Session, tenant_id: str) -> dict:
    return {
        "tenant_id": tenant_id,
        "percentiles": {m: horizon_benchmark_service.get_tenant_benchmark_percentile(db, tenant_id, m) for m in BENCHMARK_METRICS},
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
