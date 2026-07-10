"""v3.0 — Project Sentinel, Section 6: Supervisor Intelligence.

A curated view for supervisors — not a new detection engine. Composes
what the risk monitor, watchlists, digital twin monitor, competency
intelligence (Quality Guardian), and recommendation engine already found,
filtered to what a supervisor specifically needs to act on.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.sentinel_orchestration import (
    RECOMMEND_REVIEW_IFU,
    SIGNAL_REPEATED_BLOOD,
    SIGNAL_REPEATED_BONE,
    SIGNAL_REPEATED_CORROSION,
    SIGNAL_REPEATED_REPAIR_REFERRALS,
    SIGNAL_REPEATED_RUST,
    WATCHLIST_INSTRUMENT,
    WATCHLIST_INSTRUMENT_FAMILY,
)
from app.services import sentinel_recommendation_service, sentinel_risk_monitor_service, sentinel_watchlist_service
from app.services.anatomy_risk_service import anatomy_risk_dashboard
from app.services.competency_intelligence_service import list_opportunities

_CONTAMINATION_SIGNALS = {SIGNAL_REPEATED_BLOOD, SIGNAL_REPEATED_BONE, SIGNAL_REPEATED_RUST, SIGNAL_REPEATED_CORROSION}


def supervisor_intelligence_summary(db: Session, tenant_id: str) -> dict:
    watchlist = sentinel_watchlist_service.list_active_watchlist(db, tenant_id)
    signals = sentinel_risk_monitor_service.list_open_signals(db, tenant_id)
    recommendations = sentinel_recommendation_service.list_recommendations(db, tenant_id, status="open")

    high_risk_instruments = [w for w in watchlist if w["entity_type"] in (WATCHLIST_INSTRUMENT, WATCHLIST_INSTRUMENT_FAMILY)]
    high_risk_instrument_values = {w["entity_value"] for w in high_risk_instruments}
    awaiting_review_count = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id, models.Inspection.supervisor_review_required.is_(True),
            models.Inspection.instrument_type.in_(high_risk_instrument_values) if high_risk_instrument_values else False,
        )
        .count()
    ) if high_risk_instrument_values else 0

    anatomy = anatomy_risk_dashboard(db, tenant_id)

    return {
        "high_risk_instruments_awaiting_review": {
            "instruments": high_risk_instruments, "awaiting_review_count": awaiting_review_count,
        },
        "recurring_technician_education_needs": list_opportunities(db, tenant_id, status="open"),
        "coverage_gaps": {
            "incomplete_pct": anatomy["coverage_incomplete_pct"],
            "incomplete_inspections": anatomy["coverage_incomplete_inspections"],
        },
        "unusual_contamination_trends": [s for s in signals if s["signal_type"] in _CONTAMINATION_SIGNALS],
        "repeated_repair_referrals": [s for s in signals if s["signal_type"] == SIGNAL_REPEATED_REPAIR_REFERRALS],
        "potential_ifu_conflicts": [r for r in recommendations if r["recommendation_type"] == RECOMMEND_REVIEW_IFU],
        "human_review_required": True,
    }
