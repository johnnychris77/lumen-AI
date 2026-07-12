"""Project Sentinel-X, Section 10: Supervisor Workspace."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.sentinelx_risk import RISK_LEVEL_CRITICAL, RISK_LEVEL_HIGH, SentinelXRiskAssessment
from app.services.sentinelx_risk_agent_service import to_dict


def supervisor_workspace_summary(db: Session, tenant_id: str, *, limit: int = 20) -> dict:
    rows = (
        db.query(SentinelXRiskAssessment)
        .filter(SentinelXRiskAssessment.tenant_id == tenant_id)
        .order_by(SentinelXRiskAssessment.created_at.desc())
        .all()
    )

    highest_risk_inspections = sorted(
        [r for r in rows if r.inspection_id is not None], key=lambda r: r.risk_score, reverse=True,
    )[:limit]

    by_instrument: dict[str, list[SentinelXRiskAssessment]] = defaultdict(list)
    for r in rows:
        by_instrument[r.instrument_identity].append(r)
    highest_risk_instruments = sorted(
        ({"instrument_identity": k, "average_risk_score": round(sum(x.risk_score for x in v) / len(v), 1), "assessment_count": len(v)} for k, v in by_instrument.items()),
        key=lambda x: x["average_risk_score"], reverse=True,
    )[:limit]

    pending_reviews = [r for r in rows if r.risk_level in (RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL) and r.human_review_required]

    critical_anatomy = defaultdict(int)
    for r in rows:
        if r.risk_level == RISK_LEVEL_CRITICAL and r.anatomy_zone:
            critical_anatomy[r.anatomy_zone] += 1

    escalating_trends = [
        {"instrument_identity": k, "declining_count": sum(1 for x in v if x.digital_twin_condition_trend == "declining")}
        for k, v in by_instrument.items() if sum(1 for x in v if x.digital_twin_condition_trend == "declining") >= 2
    ]

    recommended_priorities = [
        {"instrument_identity": r.instrument_identity, "risk_level": r.risk_level, "reasoning_narrative": r.reasoning_narrative}
        for r in sorted(rows, key=lambda r: r.risk_score, reverse=True)[:5]
    ]

    return {
        "highest_risk_inspections": [to_dict(r) for r in highest_risk_inspections],
        "highest_risk_instruments": highest_risk_instruments,
        "pending_reviews": [to_dict(r) for r in pending_reviews[:limit]],
        "critical_anatomy": dict(critical_anatomy),
        "escalating_trends": escalating_trends,
        "recommended_priorities": recommended_priorities,
    }
