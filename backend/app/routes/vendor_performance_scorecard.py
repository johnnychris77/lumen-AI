from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/enterprise/vendor-governance/performance-scorecard",
    tags=["Vendor Performance Scorecard"],
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _performance_band(score: int) -> str:
    if score >= 85:
        return "preferred"
    if score >= 70:
        return "acceptable"
    if score >= 50:
        return "watch"
    return "corrective_action_required"


def _governance_priority(score: int, high_risk_events: int, unresolved_events: int) -> str:
    if score < 50 or high_risk_events >= 2 or unresolved_events >= 3:
        return "executive_review"
    if score < 70 or high_risk_events >= 1:
        return "leadership_watch"
    if unresolved_events >= 1:
        return "manager_follow_up"
    return "routine_monitoring"


@router.get("/health")
def vendor_performance_scorecard_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "module": "vendor_performance_scorecard",
        "version": "v1",
        "timestamp": _utc_now(),
        "capabilities": [
            "vendor_performance_scoring",
            "high_risk_vendor_detection",
            "repeat_event_tracking",
            "capa_linkage_visibility",
            "vendor_governance_decision_support",
        ],
    }


@router.get("")
@router.get("/")
def vendor_performance_scorecard() -> Dict[str, Any]:
    vendor_items: List[Dict[str, Any]] = [
        {
            "vendor_name": "OrthoTech Instruments",
            "total_vendor_events": 8,
            "high_risk_events": 3,
            "repeat_events": 4,
            "capa_linked_events": 2,
            "unresolved_events": 3,
            "average_days_open": 14,
            "vendor_score": 46,
            "performance_band": _performance_band(46),
            "governance_priority": _governance_priority(46, 3, 3),
            "recommended_action": "Escalate to executive vendor review and require formal corrective action plan.",
        },
        {
            "vendor_name": "Precision Spine Systems",
            "total_vendor_events": 5,
            "high_risk_events": 1,
            "repeat_events": 2,
            "capa_linked_events": 1,
            "unresolved_events": 1,
            "average_days_open": 8,
            "vendor_score": 68,
            "performance_band": _performance_band(68),
            "governance_priority": _governance_priority(68, 1, 1),
            "recommended_action": "Place vendor on leadership watch and review recurrence at next governance huddle.",
        },
        {
            "vendor_name": "Surgical Supply Partners",
            "total_vendor_events": 3,
            "high_risk_events": 0,
            "repeat_events": 1,
            "capa_linked_events": 0,
            "unresolved_events": 1,
            "average_days_open": 5,
            "vendor_score": 78,
            "performance_band": _performance_band(78),
            "governance_priority": _governance_priority(78, 0, 1),
            "recommended_action": "Monitor open event and verify closure documentation.",
        },
        {
            "vendor_name": "SterilePack Logistics",
            "total_vendor_events": 2,
            "high_risk_events": 0,
            "repeat_events": 0,
            "capa_linked_events": 0,
            "unresolved_events": 0,
            "average_days_open": 2,
            "vendor_score": 91,
            "performance_band": _performance_band(91),
            "governance_priority": _governance_priority(91, 0, 0),
            "recommended_action": "Continue routine monitoring and maintain current vendor status.",
        },
    ]

    scores = [item["vendor_score"] for item in vendor_items]
    average_vendor_score = round(sum(scores) / len(scores))

    high_risk_vendor_count = sum(1 for item in vendor_items if item["high_risk_events"] > 0)
    repeat_event_vendor_count = sum(1 for item in vendor_items if item["repeat_events"] > 1)
    capa_linked_vendor_count = sum(1 for item in vendor_items if item["capa_linked_events"] > 0)
    executive_review_count = sum(
        1 for item in vendor_items if item["governance_priority"] == "executive_review"
    )
    leadership_watch_count = sum(
        1 for item in vendor_items if item["governance_priority"] == "leadership_watch"
    )

    if executive_review_count > 0:
        overall_status = "action_required"
    elif leadership_watch_count > 0:
        overall_status = "leadership_watch"
    else:
        overall_status = "controlled"

    return {
        "status": "success",
        "module": "vendor_performance_scorecard",
        "version": "v1",
        "timestamp": _utc_now(),
        "overall_vendor_performance_status": overall_status,
        "average_vendor_score": average_vendor_score,
        "high_risk_vendor_count": high_risk_vendor_count,
        "repeat_event_vendor_count": repeat_event_vendor_count,
        "capa_linked_vendor_count": capa_linked_vendor_count,
        "executive_review_count": executive_review_count,
        "leadership_watch_count": leadership_watch_count,
        "vendor_performance_items": vendor_items,
        "executive_recommendations": [
            "Review vendors with executive_review priority before routine vendor performance discussion.",
            "Link repeat high-risk vendor events to CAPA Governance for accountability tracking.",
            "Use vendor_score and performance_band to support vendor scorecards and business reviews.",
            "Trend unresolved vendor events and CAPA-linked vendor events in Power BI.",
        ],
        "next_actions": [
            {
                "priority": "high",
                "action": "Create Vendor Performance Scorecard frontend cards.",
                "rationale": "Make vendor performance scoring visible to executive and quality leaders.",
            },
            {
                "priority": "high",
                "action": "Connect vendor scoring to live Vendor Governance events.",
                "rationale": "Move from deterministic scorecard examples to operational vendor performance intelligence.",
            },
            {
                "priority": "medium",
                "action": "Add vendor_score, performance_band, and governance_priority to Power BI exports.",
                "rationale": "Enable executive dashboard filtering and vendor trend analysis.",
            },
        ],
        "strategic_theme": (
            "Vendor Governance -> Vendor Performance Scoring -> "
            "CAPA Linkage -> Executive Vendor Accountability"
        ),
    }
