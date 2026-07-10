"""v3.0 — Project Sentinel, Section 8: Recommendation Engine.

Every recommendation is derived from a real, already-detected signal
(risk signal, watchlist entry, digital twin flag, AI health gap, or
Quality Guardian competency opportunity) — never a bare model suggestion.
`reasoning` always names the specific trigger.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.baseline_library import BaselineLibraryEntry
from app.models.sentinel_orchestration import (
    RECOMMEND_CREATE_BASELINE,
    RECOMMEND_EXPAND_KNOWLEDGE_GRAPH,
    RECOMMEND_REVIEW_COMPETENCY,
    RECOMMEND_REVIEW_DIGITAL_TWIN,
    RECOMMEND_REVIEW_IFU,
    RECOMMEND_SCHEDULE_EDUCATION,
    RECOMMEND_UPDATE_ANATOMY_PROFILE,
    RECOMMEND_UPDATE_SOP,
    SIGNAL_REPEATED_BLOOD,
    SIGNAL_REPEATED_BONE,
    SIGNAL_REPEATED_DAMAGE,
    SIGNAL_REPEATED_LOW_CONFIDENCE,
    SIGNAL_REPEATED_MISSING_COVERAGE,
    TWIN_TIER_CRITICAL,
    TWIN_TIER_ESCALATION,
    WATCHLIST_ANATOMY,
    WATCHLIST_INSTRUMENT,
    WATCHLIST_INSTRUMENT_FAMILY,
    SentinelRecommendation,
)
from app.services import sentinel_ai_health_service, sentinel_digital_twin_monitor_service, sentinel_risk_monitor_service, sentinel_watchlist_service
from app.services.instrument_zones import is_high_retention

_KG_SAMPLE_SIZE_FLOOR = 30
_SOP_TRIGGER_SIGNALS = {SIGNAL_REPEATED_BLOOD, SIGNAL_REPEATED_BONE, SIGNAL_REPEATED_DAMAGE}


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _already_open(db: Session, tenant_id: str, recommendation_type: str, target_description: str) -> bool:
    return (
        db.query(SentinelRecommendation.id)
        .filter(
            SentinelRecommendation.tenant_id == tenant_id, SentinelRecommendation.recommendation_type == recommendation_type,
            SentinelRecommendation.target_description == target_description, SentinelRecommendation.status == "open",
        )
        .first()
        is not None
    )


def _emit(db: Session, tenant_id: str, created: list, *, recommendation_type: str, target_description: str, reasoning: str) -> None:
    if _already_open(db, tenant_id, recommendation_type, target_description):
        return
    row = SentinelRecommendation(
        tenant_id=tenant_id, recommendation_type=recommendation_type,
        target_description=target_description, reasoning=reasoning,
    )
    db.add(row)
    created.append(row)


def generate_recommendations(db: Session, tenant_id: str) -> list[dict]:
    created: list[SentinelRecommendation] = []

    signals = sentinel_risk_monitor_service.list_open_signals(db, tenant_id)
    watchlist = sentinel_watchlist_service.list_active_watchlist(db, tenant_id)
    twin_flags = sentinel_digital_twin_monitor_service.list_open_flags(db, tenant_id)
    ai_health = sentinel_ai_health_service.compute_ai_health(db, tenant_id)

    for signal in signals:
        if signal["signal_type"] in _SOP_TRIGGER_SIGNALS and signal["severity"] in ("high", "critical"):
            _emit(
                db, tenant_id, created, recommendation_type=RECOMMEND_UPDATE_SOP, target_description=signal["scope"],
                reasoning=f"{signal['detail']} A recurring pattern at this severity suggests the current SOP for "
                          "this step may not be sufficient — review and update it.",
            )
        if signal["signal_type"] in (SIGNAL_REPEATED_LOW_CONFIDENCE, SIGNAL_REPEATED_MISSING_COVERAGE):
            _emit(
                db, tenant_id, created, recommendation_type=RECOMMEND_REVIEW_COMPETENCY, target_description=signal["scope"],
                reasoning=signal["detail"],
            )
        if is_high_retention(signal["scope"]):
            _emit(
                db, tenant_id, created, recommendation_type=RECOMMEND_REVIEW_IFU, target_description=signal["scope"],
                reasoning=f"{signal['detail']} {signal['scope']} is a high-retention zone — recurring findings here "
                          "warrant checking whether current practice matches the manufacturer's IFU for this zone.",
            )

    for entry in watchlist:
        if entry["entity_type"] == WATCHLIST_ANATOMY:
            _emit(
                db, tenant_id, created, recommendation_type=RECOMMEND_UPDATE_ANATOMY_PROFILE, target_description=entry["entity_value"],
                reasoning=entry["reason"],
            )
        if entry["entity_type"] in (WATCHLIST_INSTRUMENT, WATCHLIST_INSTRUMENT_FAMILY):
            has_approved_baseline = (
                db.query(BaselineLibraryEntry.id)
                .filter(BaselineLibraryEntry.instrument_category == entry["entity_value"], BaselineLibraryEntry.approval_status == "approved")
                .first()
                is not None
            )
            if not has_approved_baseline:
                _emit(
                    db, tenant_id, created, recommendation_type=RECOMMEND_CREATE_BASELINE, target_description=entry["entity_value"],
                    reasoning=f"{entry['reason']} No approved baseline exists for {entry['entity_value']} today.",
                )

    for flag in twin_flags:
        if flag["tier"] in (TWIN_TIER_CRITICAL, TWIN_TIER_ESCALATION):
            _emit(
                db, tenant_id, created, recommendation_type=RECOMMEND_REVIEW_DIGITAL_TWIN, target_description=flag["instrument_identity"],
                reasoning=flag["reason"],
            )

    if ai_health.get("kg_sample_size", 0) < _KG_SAMPLE_SIZE_FLOOR:
        _emit(
            db, tenant_id, created, recommendation_type=RECOMMEND_EXPAND_KNOWLEDGE_GRAPH, target_description="tenant-wide",
            reasoning=f"Only {ai_health.get('kg_sample_size', 0)} supervisor reviews back the Knowledge Graph's "
                      f"confidence today (floor: {_KG_SAMPLE_SIZE_FLOOR}) — more reviewed cases are needed before "
                      "its recommendations can be trusted at scale.",
        )

    from app.services.competency_intelligence_service import list_opportunities

    for opp in list_opportunities(db, tenant_id, status="open"):
        _emit(
            db, tenant_id, created, recommendation_type=RECOMMEND_SCHEDULE_EDUCATION,
            target_description=f"{opp['scope_type']}: {opp['scope_value']}",
            reasoning=opp["rationale"],
        )

    db.commit()
    for row in created:
        db.refresh(row)

    return list_recommendations(db, tenant_id)


def list_recommendations(db: Session, tenant_id: str, *, status: str = "open") -> list[dict]:
    q = db.query(SentinelRecommendation).filter(SentinelRecommendation.tenant_id == tenant_id)
    if status:
        q = q.filter(SentinelRecommendation.status == status)
    rows = q.order_by(SentinelRecommendation.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def action_recommendation(db: Session, tenant_id: str, recommendation_id: int, *, actioned_by: str) -> dict | None:
    row = db.query(SentinelRecommendation).filter(SentinelRecommendation.id == recommendation_id, SentinelRecommendation.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.status = "actioned"
    row.actioned_by = actioned_by
    row.actioned_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def dismiss_recommendation(db: Session, tenant_id: str, recommendation_id: int, *, actioned_by: str) -> dict | None:
    row = db.query(SentinelRecommendation).filter(SentinelRecommendation.id == recommendation_id, SentinelRecommendation.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.status = "dismissed"
    row.actioned_by = actioned_by
    row.actioned_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
