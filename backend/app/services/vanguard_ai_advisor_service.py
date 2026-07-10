"""v4.6 — Project Vanguard, Section 6: Executive AI Advisor.

These are dispatch targets for four new intents added directly to
`catalyst_query_engine.py`'s existing deterministic keyword classifier —
this module does not build a second natural-language engine. Every
function composes already-real Vanguard/Atlas/Orbit data; none of them
fabricates a risk, a recommendation, or a trend.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import (
    finding_trend_service,
    vanguard_benchmarking_service,
    vanguard_executive_intelligence_service,
    vanguard_financial_service,
)
from app.services.platform_org_service import facility_for_tenant


def top_enterprise_risks(db: Session, tenant_id: str) -> dict:
    center = vanguard_executive_intelligence_service.executive_intelligence_center(db, tenant_id)
    alerts = center["enterprise_risk"]["enterprise_alerts"]
    return {
        "top_risks": alerts[:5], "enterprise_risk_score": center["enterprise_readiness"]["enterprise_risk_score"],
        "drift_detected": center["enterprise_readiness"]["drift_detected"],
    }


def investment_recommendation(db: Session, tenant_id: str) -> dict:
    financial = vanguard_financial_service.financial_intelligence(db, tenant_id)
    return {
        "capital_replacement_priorities": financial["capital_replacement_priorities"],
        "avoided_replacement_cost_usd": financial["avoided_replacement_cost_usd"],
        "recommended_actions": financial["recommended_actions"],
        "data_source": financial["data_source"],
    }


def facilities_requiring_attention(db: Session, tenant_id: str) -> dict:
    facility = facility_for_tenant(db, tenant_id)
    if facility is None:
        return {"facilities": [], "note": "No enterprise-hierarchy facility on record for this tenant."}
    programs = vanguard_benchmarking_service.compute_benchmark(db, tenant_id, facility["system_id"], "inspection_programs")
    ranked = sorted(
        programs["results"]["inspection_programs"], key=lambda f: f["inspection_quality_pct"] or 0,
    )
    return {"facilities_requiring_attention": ranked[:5]}


def quality_trends_for_meeting(db: Session, tenant_id: str) -> dict:
    trends = finding_trend_service.finding_trends(db, tenant_id)
    top = sorted(trends["totals"].items(), key=lambda kv: kv[1], reverse=True)[:3]
    return {"top_finding_types": [{"finding_type": k, "count": v} for k, v in top], "series": trends["series"]}
