"""v4.6 — Project Vanguard, Section 3: Financial Intelligence.

Every dollar figure here is read from `prediction_engine.compute_predictive_
dashboard`, which already computes real repair/replacement cost
projections from `estimated_repair_cost_usd`/`estimated_replacement_cost_usd`
fields — nothing here re-derives a cost from scratch. `data_source` is
always surfaced verbatim (prediction_engine falls back to seeded mock
data when no real `RepairForecast` rows exist yet) so a mock projection
is never presented as if it were real.

"Inspection cost trends" is the one dimension this codebase has no real
per-inspection labor/reagent cost data for anywhere (confirmed: no cost
field on `Inspection`, no cost field on `RepairRequest`). Rather than
invent a dollar figure, this reports the real inspection-volume trend as
an explicit operational proxy, labeled as such.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.services import digital_twin_engine, or_connect_service, prediction_engine


def _inspection_volume_trend(db: Session, tenant_id: str, *, months: int = 6) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=30 * months)
    rows = db.query(Inspection).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since).all()
    buckets: dict[str, int] = {}
    for r in rows:
        key = r.created_at.strftime("%Y-%m")
        buckets[key] = buckets.get(key, 0) + 1
    return [{"month": k, "inspection_count": v} for k, v in sorted(buckets.items())]


def financial_intelligence(db: Session, tenant_id: str, *, facility_id: str = "") -> dict:
    predictive = prediction_engine.compute_predictive_dashboard(tenant_id, facility_id, db)
    twin_dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, facility_id, db)
    clinical_engineering = or_connect_service.clinical_engineering_summary(db, tenant_id)

    capital_replacement_priorities = [
        {
            "instrument_name": i["instrument_name"], "risk_score": i["risk_score"],
            "recommended_action": i["recommended_action"],
        }
        for i in predictive.highest_risk_instruments
    ]

    return {
        "data_source": predictive.data_source,
        "inspection_cost_trend_note": (
            "No per-inspection labor/reagent cost is tracked anywhere in this system — "
            "inspection volume is reported as the closest real operational proxy."
        ),
        "inspection_volume_trend": _inspection_volume_trend(db, tenant_id),
        "repair_cost_trend_usd": predictive.projected_repair_cost_usd,
        "avoided_replacement_cost_usd": predictive.repair_avoidance_roi_usd,
        "capital_replacement_priorities": capital_replacement_priorities,
        "instrument_utilization_pct": twin_dashboard.twin_state.utilization_pct,
        "reprocessing_efficiency": {
            "avg_repair_turnaround_days": clinical_engineering["avg_turnaround_days"],
            "note": "Repair turnaround is the closest real reprocessing-efficiency signal this system tracks.",
        },
        "projected_replacement_cost_usd": predictive.projected_replacement_cost_usd,
        "recommended_actions": predictive.recommended_actions,
        "human_review_required": True,
    }
