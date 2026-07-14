"""P15: National SPD Intelligence Network — benchmark engine service.

compute_industry_benchmarks() only ever returns a real, computed value for a
metric once something has written a real IndustryBenchmark row for it --
nothing in this codebase does that yet, so every metric today reports
data_source="insufficient_data" rather than a fabricated number. This
mechanism previously filled that gap with a seeded-random value dressed up
with real Laplace noise, which made a fabricated statistic indistinguishable
from a genuine cross-organization one. Per the Product Truth Reset program,
a dead/fabricated mechanism must be wired fully, disabled visibly, or
removed -- computing 6 real cross-tenant metrics correctly is new work
outside this program's "no new features" scope, so this is disabled
visibly instead.
"""
from __future__ import annotations

import math
import random
from typing import Any

from sqlalchemy.orm import Session

from app.models.network_benchmark import IndustryBenchmark, NetworkParticipant

METRICS = [
    "contamination_rate",
    "inspection_pass_rate",
    "baseline_adoption_rate",
    "instrument_quality_score",
    "vendor_performance_score",
    "override_rate",
]

MIN_FACILITIES = 5  # k-anonymity minimum


def _add_laplace_noise(value: float, sensitivity: float = 0.01, epsilon: float = 0.1) -> float:
    """Add Laplace noise for differential privacy.

    Kept here (rather than moved) because horizon_benchmark_service.py --
    the real, wired cross-org benchmarking engine -- imports this directly
    to reuse the exact same noise mechanism on its genuinely-computed
    per-tenant values.
    """
    scale = sensitivity / epsilon
    rng = random.Random()
    u = rng.uniform(-0.4999, 0.4999)
    noise = -scale * math.copysign(1, u) * math.log(1 - 2 * abs(u))
    return max(0.0, min(1.0, value + noise))


def compute_industry_benchmarks(db: Session) -> list[dict[str, Any]]:
    """Aggregate across all active NetworkParticipants; enforce N>=5; add Laplace noise."""
    participants = (
        db.query(NetworkParticipant).filter(NetworkParticipant.is_active == True).all()  # noqa: E712
    )
    n = len(participants)

    results = []
    for metric_name in METRICS:
        # DB-first
        existing = (
            db.query(IndustryBenchmark)
            .filter(
                IndustryBenchmark.metric_name == metric_name,
                IndustryBenchmark.cohort == "all",
            )
            .order_by(IndustryBenchmark.benchmark_date.desc())
            .first()
        )
        if existing:
            results.append({
                "metric_name": metric_name,
                "cohort": "all",
                "n_facilities": existing.n_facilities,
                "p25": existing.p25,
                "p50": existing.p50,
                "p75": existing.p75,
                "p90": existing.p90,
                "mean": existing.mean,
                "noise_added": existing.noise_added,
                "suppressed": existing.n_facilities < MIN_FACILITIES,
                "data_source": "real",
            })
            continue

        # No real IndustryBenchmark row exists yet for this metric (true for
        # every metric today -- nothing in this codebase writes one). This
        # mechanism previously filled the gap with a seeded-random value
        # dressed up with real Laplace noise, making a fabricated number
        # indistinguishable from a genuine cross-organization statistic.
        # Disabled visibly instead: report the real participant count and an
        # honest "insufficient_data" status rather than fabricating values.
        results.append({
            "metric_name": metric_name,
            "cohort": "all",
            "n_facilities": n,
            "p25": None,
            "p50": None,
            "p75": None,
            "p90": None,
            "mean": None,
            "noise_added": False,
            "suppressed": True,
            "data_source": "insufficient_data",
        })

    return results


def get_tenant_percentile(db: Session, tenant_id: str, metric_name: str) -> dict[str, Any]:
    """Return where this tenant falls in the distribution without revealing other tenants.

    No per-tenant metric computation exists yet for any of these 6 metrics,
    so this always reports "insufficient_data" today rather than a
    fabricated percentile -- there is no real tenant_value to rank against
    a (also not-yet-real) network distribution. tenant_id is accepted (and
    will be needed once real per-tenant computation exists) but currently
    unused, which is why it isn't referenced below.
    """
    benchmarks = compute_industry_benchmarks(db)
    bm = next((b for b in benchmarks if b["metric_name"] == metric_name), None)
    if not bm or bm.get("suppressed"):
        return {
            "metric_name": metric_name,
            "percentile": None,
            "suppressed": True,
            "data_source": "insufficient_data",
        }

    # Reachable only once a real, non-suppressed IndustryBenchmark row
    # exists for this metric (nothing writes one today, so this doesn't
    # execute against current data). No per-tenant value computation exists
    # yet even in that case, so tenant_value/percentile_band stay honestly
    # null rather than being filled with a fabricated number.
    p50 = bm["p50"]
    return {
        "metric_name": metric_name,
        "tenant_value": None,
        "percentile_band": None,
        "network_p50": p50,
        "suppressed": False,
        "data_source": "insufficient_data",
    }
