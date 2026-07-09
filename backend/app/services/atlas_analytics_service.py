"""v3.1 — Project Atlas, Section 7: Enterprise Analytics.

Trends the same `FacilityIntelligenceSnapshot` history Section 5 already
persists — never a re-derivation. Each call to `atlas_dashboard_service.
enterprise_dashboard`/`refresh_all_facility_intelligence` adds one row per
facility; this module buckets that history by month/quarter/year.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.atlas_enterprise import DISCLAIMER, FacilityIntelligenceSnapshot

_TREND_METRICS = [
    "quality_score", "risk_score", "health_score", "digital_twin_health_pct",
    "supervisor_agreement_rate", "training_index", "knowledge_index",
]


def _bucket_label(dt, granularity: str) -> str:
    if granularity == "yearly":
        return f"{dt.year}"
    if granularity == "quarterly":
        return f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
    return f"{dt.year}-{dt.month:02d}"  # monthly


def enterprise_trend(db: Session, system_id: str, *, metric: str, granularity: str = "monthly") -> dict:
    if metric not in _TREND_METRICS:
        raise ValueError(f"metric must be one of {_TREND_METRICS}")
    if granularity not in ("monthly", "quarterly", "yearly"):
        raise ValueError("granularity must be one of monthly, quarterly, yearly")

    rows = (
        db.query(FacilityIntelligenceSnapshot)
        .filter(FacilityIntelligenceSnapshot.system_id == system_id)
        .order_by(FacilityIntelligenceSnapshot.created_at.asc())
        .all()
    )

    buckets: dict[str, list[float]] = {}
    for r in rows:
        value = getattr(r, metric)
        if value is None:
            continue
        label = _bucket_label(r.created_at, granularity)
        buckets.setdefault(label, []).append(value)

    series = [
        {"period": label, "value": round(sum(values) / len(values), 2), "sample_size": len(values)}
        for label, values in sorted(buckets.items())
    ]

    return {
        "system_id": system_id, "metric": metric, "granularity": granularity, "series": series,
        "human_review_required": True, "disclaimer": DISCLAIMER,
    }


def all_metrics_trend(db: Session, system_id: str, *, granularity: str = "monthly") -> dict:
    return {metric: enterprise_trend(db, system_id, metric=metric, granularity=granularity)["series"] for metric in _TREND_METRICS}
