"""v1.5 — Finding Trend Intelligence (Deliverable 2).

Aggregates real InspectionFinding rows (logged at analysis time) by finding
type and time bucket. A finding type with zero rows in a bucket reports 0,
not an omitted key — the dashboard shows the full 12-category taxonomy so
"nothing found" is visible, not silently absent.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.inspection_finding import InspectionFinding

# The twelve categories the v1.5 spec tracks. "wear" has no dedicated scoring
# KPI in the detection engine today, so it will always report 0 — an honest
# gap, not a fabricated count.
TREND_FINDING_TYPES: list[str] = [
    "blood", "bone", "tissue", "other_organic_residue", "debris",
    "rust", "corrosion", "crack", "wear", "pitting",
    "missing_component", "insulation_damage",
]

_GRANULARITY_DAYS = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 90, "yearly": 365}
_LOOKBACK_BUCKETS = {"daily": 14, "weekly": 12, "monthly": 12, "quarterly": 8, "yearly": 5}


def _bucket_label(dt: datetime, granularity: str) -> str:
    if granularity == "daily":
        return dt.strftime("%Y-%m-%d")
    if granularity == "weekly":
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if granularity == "monthly":
        return dt.strftime("%Y-%m")
    if granularity == "quarterly":
        return f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
    return str(dt.year)


def finding_trends(db: Session, tenant_id: str, granularity: str = "monthly") -> dict:
    if granularity not in _GRANULARITY_DAYS:
        granularity = "monthly"

    lookback_days = _GRANULARITY_DAYS[granularity] * _LOOKBACK_BUCKETS[granularity]
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    rows = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.tenant_id == tenant_id, InspectionFinding.created_at >= since)
        .all()
    )

    buckets: dict[str, dict[str, int]] = {}
    for r in rows:
        label = _bucket_label(r.created_at, granularity)
        bucket = buckets.setdefault(label, {ft: 0 for ft in TREND_FINDING_TYPES})
        if r.finding_type in bucket:
            bucket[r.finding_type] += 1

    series = [
        {"period": label, "counts": counts}
        for label, counts in sorted(buckets.items())
    ]

    totals = {ft: sum(b["counts"][ft] for b in series) for ft in TREND_FINDING_TYPES}

    return {
        "granularity": granularity,
        "series": series,
        "totals": totals,
        "human_review_required": True,
    }
