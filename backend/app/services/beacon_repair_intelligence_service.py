"""v3.5 — Project Beacon, Section 7: Repair Intelligence.

Aggregates real `RepairRequest.failure_category` rows across every tenant
into a persisted `RepairIntelligenceSnapshot` (new additive table,
`app/models/industry_collaboration.py`) — the same "compute once, persist
the aggregate, never re-derive raw rows in the response" pattern
`network_benchmark_service.py` and `CaseReadinessScoreRecord` already use
in this codebase. Suppressed below `MIN_FACILITIES` contributing
hospitals, reusing the same floor as every other cross-tenant system.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.industry_collaboration import DISCLAIMER, SNAPSHOT_MONTHLY, RepairIntelligenceSnapshot
from app.models.or_connect import FAILURE_CATEGORIES, RepairRequest
from app.services.network_benchmark_service import MIN_FACILITIES

_LOOKBACK_DAYS = 90


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def generate_snapshot(db: Session, failure_category: str, *, period: str = SNAPSHOT_MONTHLY) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    repairs = db.query(RepairRequest).filter(
        RepairRequest.failure_category == failure_category, RepairRequest.created_at >= since,
    ).all()

    facility_count = len({r.tenant_id for r in repairs})
    suppressed = facility_count < MIN_FACILITIES

    repeat_rate = None
    avg_turnaround = None
    recommendation = ""
    if not suppressed and repairs:
        by_instrument: dict[str, int] = {}
        for r in repairs:
            if r.instrument_identity:
                by_instrument[r.instrument_identity] = by_instrument.get(r.instrument_identity, 0) + 1
        repeats = sum(1 for v in by_instrument.values() if v > 1)
        repeat_rate = round(repeats / len(by_instrument), 4) if by_instrument else None

        completed = [r for r in repairs if r.actual_return_date is not None]
        if completed:
            avg_turnaround = round(sum((r.actual_return_date - r.created_at).days for r in completed) / len(completed), 1)

        recommendation = (
            f"'{failure_category}' repairs recurred across {facility_count} contributing facilities in the "
            f"last {_LOOKBACK_DAYS} days ({len(repairs)} repairs). Possible contributing factor: instrument "
            "handling, sterilization cycle, or manufacturing variance — not a confirmed root cause. "
            "Quality review recommended."
        )

    snapshot = RepairIntelligenceSnapshot(
        period=period, failure_category=failure_category, facility_count=facility_count,
        total_repairs=len(repairs), repeat_repair_rate=repeat_rate, avg_turnaround_days=avg_turnaround,
        quality_improvement_recommendation=recommendation, suppressed=suppressed,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return _row_to_dict(snapshot)


def generate_all_snapshots(db: Session, *, period: str = SNAPSHOT_MONTHLY) -> list[dict]:
    return [generate_snapshot(db, cat, period=period) for cat in FAILURE_CATEGORIES]


def list_snapshots(db: Session, *, failure_category: str = "") -> list[dict]:
    q = db.query(RepairIntelligenceSnapshot)
    if failure_category:
        q = q.filter(RepairIntelligenceSnapshot.failure_category == failure_category)
    rows = q.order_by(RepairIntelligenceSnapshot.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def repair_intelligence_summary(db: Session) -> dict:
    snapshots = list_snapshots(db)
    published = [s for s in snapshots if not s["suppressed"]]
    return {
        "snapshots": snapshots,
        "published_count": len(published),
        "suppressed_count": len(snapshots) - len(published),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
