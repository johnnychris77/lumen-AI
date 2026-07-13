"""P15: National SPD Intelligence Network — benchmark engine service."""
from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime
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


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def _anonymize_facility_id(facility_id: str, month_salt: str) -> str:
    """SHA-256 pseudonymization with monthly salt rotation."""
    digest = hashlib.sha256(f"{facility_id}{month_salt}".encode()).hexdigest()
    return digest[:12]


def _add_laplace_noise(value: float, sensitivity: float = 0.01, epsilon: float = 0.1) -> float:
    """Add Laplace noise for differential privacy."""
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
    month_salt = datetime.utcnow().strftime("%Y-%m")

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

        # Seeded mock fallback -- reached whenever no real IndustryBenchmark
        # row exists yet for this metric (which is always, today: nothing in
        # this codebase currently writes one). These values are generated
        # from a deterministic RNG seed, not read from any NetworkParticipant
        # activity -- `data_source: "fabricated_demo"` makes that explicit to
        # every caller instead of looking identical to a real, noised
        # cross-organization statistic.
        effective_n = max(n, MIN_FACILITIES)
        rng = _seed(f"benchmark:{metric_name}:{month_salt}")
        values = sorted([rng.uniform(0.6, 0.99) for _ in range(effective_n)])

        p25 = round(_add_laplace_noise(values[int(0.25 * len(values))]), 4)
        p50 = round(_add_laplace_noise(values[int(0.50 * len(values))]), 4)
        p75 = round(_add_laplace_noise(values[int(0.75 * len(values))]), 4)
        p90 = round(_add_laplace_noise(values[int(0.90 * len(values))]), 4)
        mean_val = round(_add_laplace_noise(sum(values) / len(values)), 4)

        results.append({
            "metric_name": metric_name,
            "cohort": "all",
            "n_facilities": effective_n,
            "p25": p25,
            "p50": p50,
            "p75": p75,
            "p90": p90,
            "mean": mean_val,
            "noise_added": True,
            "suppressed": False,
            "data_source": "fabricated_demo",
        })

    return results


def get_tenant_percentile(db: Session, tenant_id: str, metric_name: str) -> dict[str, Any]:
    """Return where this tenant falls in the distribution without revealing other tenants."""
    benchmarks = compute_industry_benchmarks(db)
    bm = next((b for b in benchmarks if b["metric_name"] == metric_name), None)
    if not bm or bm.get("suppressed"):
        return {"metric_name": metric_name, "percentile": None, "suppressed": True}

    # No per-tenant metric is ever read here -- this value is generated from
    # a deterministic RNG seed, the same as compute_industry_benchmarks()'s
    # fallback above. Always mark it fabricated rather than letting it read
    # as this tenant's real computed standing.
    rng = _seed(f"percentile:{tenant_id}:{metric_name}")
    tenant_value = round(rng.uniform(0.70, 0.98), 4)

    p25 = bm["p25"] or 0
    p50 = bm["p50"] or 0
    p75 = bm["p75"] or 0
    p90 = bm["p90"] or 0

    if tenant_value < p25:
        percentile_band = "below_p25"
    elif tenant_value < p50:
        percentile_band = "p25_to_p50"
    elif tenant_value < p75:
        percentile_band = "p50_to_p75"
    elif tenant_value < p90:
        percentile_band = "p75_to_p90"
    else:
        percentile_band = "above_p90"

    return {
        "metric_name": metric_name,
        "tenant_value": tenant_value,
        "percentile_band": percentile_band,
        "network_p50": p50,
        "suppressed": False,
        "data_source": "fabricated_demo",
    }
