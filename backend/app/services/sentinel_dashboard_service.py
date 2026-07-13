"""v3.0 — Project Sentinel, Section 7: Executive Sentinel Dashboard.

The Enterprise Risk Score deliberately composes `quality_dashboard_service.
executive_quality_score` (a real, weighted 0-100 process-quality score)
rather than re-deriving pass-rate/coverage/agreement math a third time.
It is NOT a copy of `QualityTwinState.overall_quality_score` — that score
is currently a seeded-mock placeholder pending real multi-source wiring
(see `digital_quality_twin_service.py`'s `_NINE_SOURCES`); this one reads
only real data and, like `executive_quality_score`, excludes any factor
with no underlying data rather than defaulting it to a fabricated value.
It is also framed inversely on purpose — 0-100 where HIGHER means MORE
risk — the opposite convention from the existing quality score, because
"risk score" reads more naturally that way; this is documented so the two
scores are never confused.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.sentinel_orchestration import DISCLAIMER, SentinelHealthSnapshot
from app.services import (
    sentinel_ai_health_service,
    sentinel_alert_service,
    sentinel_digital_twin_monitor_service,
    sentinel_risk_monitor_service,
    sentinel_watchlist_service,
)
from app.services.or_connect_service import executive_dashboard as or_connect_executive_dashboard
from app.services.quality_dashboard_service import executive_quality_score
from app.services.workflow_notification_service import list_notifications

_RISK_WEIGHTS = {
    "quality_risk": 0.50,
    "watchlist_pressure": 0.20,
    "alert_pressure": 0.20,
    "drift_risk": 0.10,
}


def _compute_enterprise_risk_score(db: Session, tenant_id: str, ai_health: dict) -> tuple[int, dict]:
    quality = executive_quality_score(db, tenant_id)
    quality_score = quality.get("score")

    watchlist_count = len(sentinel_watchlist_service.list_active_watchlist(db, tenant_id))
    alerts = sentinel_alert_service.list_alerts(db, tenant_id, unresolved_only=True)
    high_critical_alerts = sum(1 for a in alerts if a["severity"] in ("high", "critical"))

    factors = {}
    if quality_score is not None:
        # quality_score can fall outside 0-100 (e.g. repeat_rate > 100% when
        # repeated-error events outnumber supervisor-correction events), so
        # clamp like every other factor to keep the composite score in range.
        factors["quality_risk"] = max(0, min(100, 100 - quality_score))
    factors["watchlist_pressure"] = min(100, watchlist_count * 10)
    factors["alert_pressure"] = min(100, high_critical_alerts * 15)
    factors["drift_risk"] = 100 if ai_health.get("drift_detected") else 0

    total_weight = sum(_RISK_WEIGHTS[k] for k in factors)
    score = round(sum(_RISK_WEIGHTS[k] * v for k, v in factors.items()) / total_weight) if total_weight else 0

    return score, {"factors": factors, "weights": _RISK_WEIGHTS, "quality_score_used": quality_score}


def run_sentinel_health_snapshot(db: Session, tenant_id: str) -> dict:
    ai_health = sentinel_ai_health_service.compute_ai_health(db, tenant_id)
    risk_score, risk_breakdown = _compute_enterprise_risk_score(db, tenant_id, ai_health)

    snapshot = SentinelHealthSnapshot(
        tenant_id=tenant_id, enterprise_risk_score=risk_score,
        ai_confidence_avg=ai_health.get("ai_confidence_avg"),
        supervisor_agreement_rate=ai_health.get("supervisor_agreement_rate"),
        false_positive_rate=ai_health.get("false_positive_rate"),
        false_negative_rate=ai_health.get("false_negative_rate"),
        coverage_quality_pct=ai_health.get("coverage_quality_pct"),
        baseline_quality_pct=ai_health.get("baseline_quality_pct"),
        kg_confidence=ai_health.get("kg_confidence"),
        kg_sample_size=ai_health.get("kg_sample_size", 0),
        drift_detected=ai_health.get("drift_detected", False),
        drift_detail=ai_health.get("drift_detail", ""),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    result = {col.name: getattr(snapshot, col.name) for col in snapshot.__table__.columns}
    result["created_at"] = result["created_at"].isoformat()
    result["risk_score_breakdown"] = risk_breakdown
    return result


def knowledge_growth_trend(db: Session, tenant_id: str, *, days: int = 90) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(SentinelHealthSnapshot)
        .filter(SentinelHealthSnapshot.tenant_id == tenant_id, SentinelHealthSnapshot.created_at >= since)
        .order_by(SentinelHealthSnapshot.created_at.asc())
        .all()
    )
    return [
        {"date": r.created_at.isoformat(), "kg_confidence": r.kg_confidence, "kg_sample_size": r.kg_sample_size}
        for r in rows
    ]


def _facility_comparison(db: Session, tenant_id: str) -> list[dict]:
    rows = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id, models.Inspection.facility_name.isnot(None)).all()
    by_facility: dict[str, list] = {}
    for r in rows:
        by_facility.setdefault(r.facility_name, []).append(r)
    result = []
    for facility, insp_rows in by_facility.items():
        scored = [r for r in insp_rows if r.score_status in ("scored", "scored_after_override")]
        passed = [r for r in scored if r.disposition == "PASS"]
        result.append({
            "facility": facility, "total_inspections": len(insp_rows),
            "pass_rate_pct": round(100 * len(passed) / len(scored), 1) if scored else None,
        })
    return sorted(result, key=lambda x: x["total_inspections"], reverse=True)


def executive_sentinel_dashboard(db: Session, tenant_id: str) -> dict:
    snapshot = run_sentinel_health_snapshot(db, tenant_id)
    alerts = sentinel_alert_service.list_alerts(db, tenant_id, unresolved_only=True)
    critical_findings = [a for a in alerts if a["severity"] == "critical"]
    watchlist = sentinel_watchlist_service.list_active_watchlist(db, tenant_id)
    twin_flags = sentinel_digital_twin_monitor_service.list_open_flags(db, tenant_id)
    top_signals = sentinel_risk_monitor_service.list_open_signals(db, tenant_id)[:10]

    inspection_count = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).count()

    supervisor_workload = {}
    for role in ("spd_manager",):
        supervisor_workload[role] = len(list_notifications(db, tenant_id, recipient_role=role, unread_only=True))

    or_connect_bottlenecks = or_connect_executive_dashboard(db, tenant_id).get("operational_bottlenecks", [])

    return {
        "enterprise_risk_score": snapshot["enterprise_risk_score"],
        "risk_score_breakdown": snapshot["risk_score_breakdown"],
        "critical_findings": critical_findings,
        "open_watchlists": watchlist,
        "model_health": {
            "ai_confidence_avg": snapshot["ai_confidence_avg"],
            "supervisor_agreement_rate": snapshot["supervisor_agreement_rate"],
            "false_positive_rate": snapshot["false_positive_rate"],
            "false_negative_rate": snapshot["false_negative_rate"],
            "drift_detected": snapshot["drift_detected"],
            "drift_detail": snapshot["drift_detail"],
        },
        "knowledge_growth": knowledge_growth_trend(db, tenant_id),
        "inspection_throughput": inspection_count,
        "facility_comparison": _facility_comparison(db, tenant_id),
        "supervisor_workload": supervisor_workload,
        "top_emerging_risks": top_signals,
        "digital_twin_flags": twin_flags,
        "operational_bottlenecks": or_connect_bottlenecks,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
