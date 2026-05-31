from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/enterprise/governance-intelligence",
    tags=["Enterprise Governance Intelligence"],
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_status(score: int) -> str:
    if score >= 85:
        return "executive_ready"
    if score >= 70:
        return "watch"
    return "action_required"


@router.get("/health")
def governance_intelligence_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "module": "enterprise_governance_intelligence",
        "version": "v1",
        "timestamp": _utc_now(),
        "capabilities": [
            "audit_signal_interpretation",
            "capa_signal_interpretation",
            "vendor_signal_interpretation",
            "powerbi_readiness_summary",
            "executive_recommendations",
            "next_action_guidance",
        ],
    }


@router.get("/summary")
def governance_intelligence_summary() -> Dict[str, Any]:
    audit_signal = {
        "domain": "audit_governance",
        "status": "ready",
        "score": 92,
        "interpretation": "Audit Command Center is released, portfolio linked, and production validated.",
        "evidence": [
            "/api/enterprise/audit-command-center/health",
            "/portfolio/audit-command-center",
        ],
    }

    capa_signal = {
        "domain": "capa_governance",
        "status": "ready",
        "score": 88,
        "interpretation": "CAPA Governance Scorecard is released with escalation visibility and Power BI export readiness.",
        "evidence": [
            "/api/capa/governance-scorecard?days_until_due=7",
            "/api/capa/powerbi-csv?limit=500",
            "/portfolio/capa-workflow",
        ],
    }

    vendor_signal = {
        "domain": "vendor_governance",
        "status": "ready",
        "score": 86,
        "interpretation": "Vendor Governance is released with vendor risk visibility, CAPA linkage, and Power BI export readiness.",
        "evidence": [
            "/api/enterprise/vendor-governance/summary",
            "/api/enterprise/vendor-governance/capa-linkage-summary",
            "/api/enterprise/vendor-governance/powerbi-csv?limit=500",
            "/portfolio/vendor-governance",
        ],
    }

    powerbi_readiness = {
        "status": "ready",
        "score": 90,
        "exports": [
            {
                "name": "CAPA Power BI CSV",
                "endpoint": "/api/capa/powerbi-csv?limit=500",
                "status": "available",
            },
            {
                "name": "Vendor Governance Power BI CSV",
                "endpoint": "/api/enterprise/vendor-governance/powerbi-csv?limit=500",
                "status": "available",
            },
        ],
    }

    signal_scores = [
        audit_signal["score"],
        capa_signal["score"],
        vendor_signal["score"],
        powerbi_readiness["score"],
    ]

    governance_health_score = round(sum(signal_scores) / len(signal_scores))
    overall_status = _score_status(governance_health_score)

    executive_recommendations: List[str] = [
        "Use the Executive Governance Dashboard as the leadership command view.",
        "Use CAPA and Vendor Power BI exports to build recurring executive scorecards.",
        "Prioritize v1.1 predictive CAPA risk scoring and vendor performance scoring.",
        "Convert governance intelligence outputs into an executive action queue.",
    ]

    next_actions: List[Dict[str, str]] = [
        {
            "priority": "high",
            "action": "Build Governance Intelligence frontend cards.",
            "owner": "LumenAI Product",
            "rationale": "Expose the new intelligence summary in the public executive dashboard.",
        },
        {
            "priority": "high",
            "action": "Implement CAPA Predictive Risk Scorecard.",
            "owner": "LumenAI Product",
            "rationale": "Move from static CAPA reporting to risk-prioritized governance decision support.",
        },
        {
            "priority": "medium",
            "action": "Implement Vendor Performance Scorecard.",
            "owner": "LumenAI Product",
            "rationale": "Translate vendor event signals into performance and accountability metrics.",
        },
    ]

    return {
        "status": "success",
        "module": "enterprise_governance_intelligence",
        "version": "v1",
        "timestamp": _utc_now(),
        "overall_governance_status": overall_status,
        "governance_health_score": governance_health_score,
        "signals": {
            "audit": audit_signal,
            "capa": capa_signal,
            "vendor": vendor_signal,
            "powerbi_readiness": powerbi_readiness,
        },
        "executive_recommendations": executive_recommendations,
        "next_actions": next_actions,
        "strategic_theme": (
            "Audit Governance -> CAPA Governance -> Vendor Governance -> "
            "Power BI Analytics -> Executive Interpretation -> Predictive Governance Intelligence"
        ),
    }
