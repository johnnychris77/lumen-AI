"""v4.6 — Project Vanguard, Section 2: Executive Scorecards.

Eight audience labels (`SCORECARD_AUDIENCES`), each a *display shape*
over the same real, already-computed Vanguard/Atlas/Orbit/Pulse data —
following the exact precedent `atlas_report_service.generate_executive_
report`'s `audience` parameter already established. RBAC is enforced by
the route (existing `require_roles` tiers), never by a new per-role
permission table; the audience label only selects which subset/framing
of real data is returned.

This deliberately does not read from or extend the pre-existing
`/api/executive/dashboard/{role}` endpoint, whose own response labels
most fields `"data_source": "mock"` — every figure below traces back to
a real computation.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.vanguard_intelligence import (
    AUDIENCE_CEO,
    AUDIENCE_CMO,
    AUDIENCE_CNO,
    AUDIENCE_COO,
    AUDIENCE_QUALITY,
    AUDIENCE_SPD_DIRECTOR,
    AUDIENCE_SUPPLY_CHAIN,
    AUDIENCE_VP_SURGICAL_SERVICES,
    SCORECARD_AUDIENCES,
    ExecutiveScorecardSnapshot,
)
from app.services import (
    vanguard_executive_intelligence_service,
    vanguard_financial_service,
    vanguard_operational_service,
)


class UnknownScorecardAudienceError(Exception):
    pass


def _kpis_for_audience(db: Session, tenant_id: str, audience: str, *, facility_id: str = "") -> dict:
    center = vanguard_executive_intelligence_service.executive_intelligence_center(db, tenant_id, facility_id=facility_id)
    financial = vanguard_financial_service.financial_intelligence(db, tenant_id, facility_id=facility_id)
    operational = vanguard_operational_service.operational_intelligence(db, tenant_id)

    if audience == AUDIENCE_CEO:
        return {
            "enterprise_risk_score": center["enterprise_readiness"]["enterprise_risk_score"],
            "surgical_readiness_pct": center["surgical_readiness"]["readiness_pct"],
            "financial_impact_usd": financial["repair_cost_trend_usd"],
            "top_enterprise_alerts": center["enterprise_risk"]["enterprise_alerts"][:5],
        }
    if audience == AUDIENCE_COO:
        return {
            "throughput": operational["throughput"], "or_delays": operational["or_delays"],
            "repair_backlog": operational["repair_backlog"], "capacity": center["capacity"],
        }
    if audience == AUDIENCE_CNO:
        return {
            "inspection_quality": operational["inspection_quality"],
            "staffing": operational["staffing"], "readiness": operational["readiness"],
        }
    if audience == AUDIENCE_CMO:
        return {
            "surgical_readiness": center["surgical_readiness"], "inspection_quality": operational["inspection_quality"],
            "readiness_trend": operational["readiness"]["case_readiness_trend"],
        }
    if audience == AUDIENCE_VP_SURGICAL_SERVICES:
        return {
            "surgical_readiness": center["surgical_readiness"], "or_delays": operational["or_delays"],
            "capacity": center["capacity"],
        }
    if audience == AUDIENCE_QUALITY:
        return {
            "spd_quality": center["spd_quality"], "inspection_quality": operational["inspection_quality"],
            "knowledge_growth": center["knowledge_growth"],
        }
    if audience == AUDIENCE_SUPPLY_CHAIN:
        return {
            "repair_backlog": operational["repair_backlog"], "instrument_availability": operational["instrument_availability"],
            "capital_replacement_priorities": financial["capital_replacement_priorities"],
        }
    if audience == AUDIENCE_SPD_DIRECTOR:
        return {
            "ai_health": center["ai_health"], "throughput": operational["throughput"],
            "repair_backlog": operational["repair_backlog"], "readiness": operational["readiness"],
        }
    raise UnknownScorecardAudienceError(f"audience must be one of {SCORECARD_AUDIENCES}")


def generate_scorecard(db: Session, tenant_id: str, audience: str, *, facility_id: str = "") -> dict:
    if audience not in SCORECARD_AUDIENCES:
        raise UnknownScorecardAudienceError(f"audience must be one of {SCORECARD_AUDIENCES}")

    kpis = _kpis_for_audience(db, tenant_id, audience, facility_id=facility_id)

    import json
    snapshot = ExecutiveScorecardSnapshot(
        tenant_id=tenant_id, audience=audience, facility_id=facility_id, kpis_json=json.dumps(kpis, default=str),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return {"id": snapshot.id, "audience": audience, "kpis": kpis, "human_review_required": True}


def scorecard_history(db: Session, tenant_id: str, audience: str, *, limit: int = 20) -> list[dict]:
    import json

    rows = (
        db.query(ExecutiveScorecardSnapshot)
        .filter(ExecutiveScorecardSnapshot.tenant_id == tenant_id, ExecutiveScorecardSnapshot.audience == audience)
        .order_by(ExecutiveScorecardSnapshot.id.desc())
        .limit(limit)
        .all()
    )
    return [{"id": r.id, "created_at": r.created_at.isoformat(), "kpis": json.loads(r.kpis_json)} for r in rows]
