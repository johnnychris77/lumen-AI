from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/capa/risk-scorecard",
    tags=["CAPA Predictive Risk Scorecard"],
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _risk_band(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 50:
        return "watch"
    return "controlled"


def _executive_priority(score: int, is_overdue: bool) -> str:
    if is_overdue or score >= 85:
        return "immediate_review"
    if score >= 70:
        return "leadership_watch"
    if score >= 50:
        return "manager_follow_up"
    return "routine_monitoring"


@router.get("/health")
def capa_predictive_risk_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "module": "capa_predictive_risk_scorecard",
        "version": "v1",
        "timestamp": _utc_now(),
        "capabilities": [
            "capa_risk_scoring",
            "overdue_risk_detection",
            "executive_priority_assignment",
            "recommended_action_guidance",
            "capa_governance_decision_support",
        ],
    }


@router.get("")
@router.get("/")
def capa_predictive_risk_scorecard() -> Dict[str, Any]:
    """
    CAPA Predictive Risk Scorecard v1.

    v1 uses deterministic demo-safe CAPA governance examples so the endpoint is stable,
    production-safe, and ready for portfolio demonstration. Later v1.1 milestones can
    wire this into live CAPA persistence and historical closure behavior.
    """

    capa_items: List[Dict[str, Any]] = [
        {
            "capa_id": "CAPA-2026-001",
            "title": "High-risk vendor tray defect recurrence",
            "source": "vendor_governance",
            "risk_level": "high",
            "status": "open",
            "owner": "Quality Governance",
            "days_to_due": 2,
            "is_overdue": False,
            "is_high_risk": True,
            "risk_score": 88,
            "risk_band": _risk_band(88),
            "executive_priority": _executive_priority(88, False),
            "recommended_action": "Escalate to executive review and require vendor corrective action update.",
        },
        {
            "capa_id": "CAPA-2026-002",
            "title": "Repeated wet tray process failures",
            "source": "audit_governance",
            "risk_level": "high",
            "status": "open",
            "owner": "Sterile Processing Leadership",
            "days_to_due": -1,
            "is_overdue": True,
            "is_high_risk": True,
            "risk_score": 94,
            "risk_band": _risk_band(94),
            "executive_priority": _executive_priority(94, True),
            "recommended_action": "Treat as immediate governance escalation due to overdue high-risk status.",
        },
        {
            "capa_id": "CAPA-2026-003",
            "title": "Incomplete documentation during audit readiness review",
            "source": "audit_governance",
            "risk_level": "medium",
            "status": "in_progress",
            "owner": "Compliance Lead",
            "days_to_due": 6,
            "is_overdue": False,
            "is_high_risk": False,
            "risk_score": 66,
            "risk_band": _risk_band(66),
            "executive_priority": _executive_priority(66, False),
            "recommended_action": "Assign manager follow-up and verify documentation closure before due date.",
        },
        {
            "capa_id": "CAPA-2026-004",
            "title": "Vendor IFU mismatch requires monitoring",
            "source": "vendor_governance",
            "risk_level": "medium",
            "status": "open",
            "owner": "Vendor Governance",
            "days_to_due": 10,
            "is_overdue": False,
            "is_high_risk": False,
            "risk_score": 58,
            "risk_band": _risk_band(58),
            "executive_priority": _executive_priority(58, False),
            "recommended_action": "Monitor vendor response and link to CAPA if recurrence is detected.",
        },
    ]

    scores = [item["risk_score"] for item in capa_items]
    average_risk_score = round(sum(scores) / len(scores))

    high_priority_count = sum(
        1 for item in capa_items if item["executive_priority"] in {"immediate_review", "leadership_watch"}
    )
    overdue_count = sum(1 for item in capa_items if item["is_overdue"])
    critical_count = sum(1 for item in capa_items if item["risk_band"] == "critical")
    watch_count = sum(1 for item in capa_items if item["risk_band"] == "watch")

    if critical_count > 0 or overdue_count > 0:
        overall_status = "action_required"
    elif high_priority_count > 0:
        overall_status = "leadership_watch"
    else:
        overall_status = "controlled"

    executive_recommendations = [
        "Review overdue and critical CAPAs first during executive governance huddles.",
        "Use risk_score and executive_priority to sequence CAPA follow-up instead of relying only on due date.",
        "Connect vendor-linked CAPAs to Vendor Governance performance scoring.",
        "Use Power BI exports to trend high-risk CAPA recurrence and closure performance.",
    ]

    next_actions = [
        {
            "priority": "high",
            "action": "Create frontend CAPA Predictive Risk Scorecard cards.",
            "rationale": "Make risk-prioritized CAPA intelligence visible to leaders.",
        },
        {
            "priority": "high",
            "action": "Connect predictive CAPA scoring to persistent CAPA records.",
            "rationale": "Move from demo-safe deterministic scoring to live operational scoring.",
        },
        {
            "priority": "medium",
            "action": "Add Power BI fields for risk_score, risk_band, and executive_priority.",
            "rationale": "Enable executive dashboard filtering and trend analysis.",
        },
    ]

    return {
        "status": "success",
        "module": "capa_predictive_risk_scorecard",
        "version": "v1",
        "timestamp": _utc_now(),
        "overall_capa_risk_status": overall_status,
        "average_risk_score": average_risk_score,
        "high_priority_count": high_priority_count,
        "overdue_count": overdue_count,
        "critical_count": critical_count,
        "watch_count": watch_count,
        "capa_risk_items": capa_items,
        "executive_recommendations": executive_recommendations,
        "next_actions": next_actions,
        "strategic_theme": (
            "CAPA Governance -> Predictive CAPA Risk Scoring -> "
            "Executive Prioritization -> Governance Intelligence"
        ),
    }
