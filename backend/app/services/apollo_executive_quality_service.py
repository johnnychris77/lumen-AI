"""v4.7 — Project Apollo, Section 10: Executive Quality Dashboard.

Composes `quality_command_center_service.quality_command_center_summary`
(v2.9) and `vanguard_governance_service.governance_dashboard` (v4.6) — the
two pre-existing systems that already compute the large majority of the
named tiles — rather than re-deriving CAPA/root-cause/competency/audit-
readiness numbers a third time. The only genuinely new computation here is
the Quality Maturity Index: an original weighted composite documented below.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import capa_lifecycle_service, quality_command_center_service, vanguard_governance_service
from app.services.apollo_improvement_portfolio_service import portfolio_summary
from app.services.apollo_policy_service import policies_due_for_review

# Quality Maturity Index weights — documented since this is the one
# genuinely new metric in this file. Compliance/audit-readiness weighted
# highest since they gate accreditation; CAPA health and continuous
# improvement weighted lower as leading (not lagging) indicators.
_QMI_WEIGHTS = {
    "compliance": 0.30,
    "capa_health": 0.20,
    "competency": 0.20,
    "continuous_improvement": 0.15,
    "policy_currency": 0.15,
}


def _quality_maturity_index(
    *, compliance_score: float, capa_closure_rate: float, competency_avg: float,
    ci_completion_rate: float, policy_currency_pct: float,
) -> float:
    return round(
        _QMI_WEIGHTS["compliance"] * compliance_score
        + _QMI_WEIGHTS["capa_health"] * capa_closure_rate
        + _QMI_WEIGHTS["competency"] * competency_avg
        + _QMI_WEIGHTS["continuous_improvement"] * ci_completion_rate
        + _QMI_WEIGHTS["policy_currency"] * policy_currency_pct,
        1,
    )


def executive_quality_dashboard(db: Session, tenant_id: str, *, tenant_name: str = "") -> dict:
    command_center = quality_command_center_service.quality_command_center_summary(db, tenant_id)
    governance = vanguard_governance_service.governance_dashboard(db, tenant_id, tenant_name=tenant_name)
    lifecycle_counts = capa_lifecycle_service.lifecycle_summary(tenant_id)
    total_capas = sum(lifecycle_counts.values())
    capa_closure_rate = (
        round(100 * lifecycle_counts.get(capa_lifecycle_service.LIFECYCLE_CLOSED, 0) / total_capas, 1)
        if total_capas else 100.0
    )
    portfolio = portfolio_summary(db, tenant_id)
    upcoming_reviews = policies_due_for_review(db, tenant_id, within_days=30)
    high_risk_policies = policies_due_for_review(db, tenant_id, within_days=0)  # already overdue

    compliance_score = governance["audit_readiness"].get("overall_readiness_score") or 0.0
    competency_avg = command_center.get("education_impact_avg_pct") or 0.0
    ci_completion_rate = portfolio["completion_rate_pct"] or 0.0
    # Each overdue-review policy deducts 10 points from a 100-point baseline
    # — a simple, honest proxy since there's no independent "policy currency"
    # metric to read; never fabricated as a measured rate.
    policy_currency_pct = max(0.0, 100.0 - 10.0 * len(high_risk_policies))

    qmi = _quality_maturity_index(
        compliance_score=compliance_score, capa_closure_rate=capa_closure_rate, competency_avg=competency_avg,
        ci_completion_rate=ci_completion_rate, policy_currency_pct=policy_currency_pct,
    )

    return {
        "compliance_score": compliance_score,
        "audit_readiness": governance["audit_readiness"],
        "open_capas": total_capas - lifecycle_counts.get(capa_lifecycle_service.LIFECYCLE_CLOSED, 0),
        "capa_closure_rate_pct": capa_closure_rate,
        "competency_status": {
            "technician_trends": command_center.get("technician_trends"),
            "education_impact_avg_pct": command_center.get("education_impact_avg_pct"),
        },
        "high_risk_policies": high_risk_policies,
        "upcoming_reviews": upcoming_reviews,
        "continuous_improvement": {
            "total_projects": portfolio["total_projects"],
            "completion_rate_pct": portfolio["completion_rate_pct"],
            "total_cost_savings_usd": portfolio["total_cost_savings_usd"],
            "executive_visible_projects": portfolio["executive_visible_projects"],
        },
        "quality_maturity_index": qmi,
        "quality_maturity_index_weights": _QMI_WEIGHTS,
        "root_causes": command_center.get("root_causes"),
        "recurring_findings": command_center.get("recurring_findings"),
        "human_review_required": True,
    }
