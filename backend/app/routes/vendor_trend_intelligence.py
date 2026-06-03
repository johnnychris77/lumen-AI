from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List
import csv

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(
    prefix="/api/v1-2/vendor/trend-intelligence",
    tags=["v1.2 Vendor Trend Intelligence"],
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_trend_band(delta: int) -> str:
    if delta <= -10:
        return "worsening"
    if delta <= -3:
        return "watch"
    if delta >= 5:
        return "improving"
    return "stable"


def _executive_priority(
    current_score: int,
    repeat_event_count: int,
    high_risk_event_count: int,
    capa_linked_event_count: int,
) -> str:
    if current_score < 65 or high_risk_event_count >= 3 or capa_linked_event_count >= 2:
        return "executive_review"
    if current_score < 75 or repeat_event_count >= 3 or high_risk_event_count >= 2:
        return "leadership_watch"
    if current_score < 85 or repeat_event_count >= 2:
        return "manager_follow_up"
    return "routine_monitoring"


def _vendor_trend_items() -> List[Dict[str, Any]]:
    return [
        {
            "vendor_name": "OrthoTech Instruments",
            "vendor_category": "Orthopedic Loaner Trays",
            "current_vendor_score": 62,
            "prior_vendor_score": 74,
            "vendor_score_delta": -12,
            "trend_band": _score_trend_band(-12),
            "repeat_event_count": 5,
            "high_risk_event_count": 3,
            "capa_linked_event_count": 2,
            "latest_event_type": "repeat_tray_quality_defect",
            "primary_site": "Market",
            "linked_capa_id": "CAPA-2026-001",
            "executive_priority": _executive_priority(62, 5, 3, 2),
            "recommended_action": "Escalate to executive vendor review and require documented corrective action with CAPA linkage.",
        },
        {
            "vendor_name": "Precision Spine Systems",
            "vendor_category": "Spine Instrumentation",
            "current_vendor_score": 69,
            "prior_vendor_score": 72,
            "vendor_score_delta": -3,
            "trend_band": _score_trend_band(-3),
            "repeat_event_count": 3,
            "high_risk_event_count": 2,
            "capa_linked_event_count": 1,
            "latest_event_type": "inspection_finding_recurrence",
            "primary_site": "ORC",
            "linked_capa_id": "CAPA-2026-003",
            "executive_priority": _executive_priority(69, 3, 2, 1),
            "recommended_action": "Place vendor on leadership watch and trend inspection recurrence during monthly governance review.",
        },
        {
            "vendor_name": "SterilePak Logistics",
            "vendor_category": "Transport and Logistics",
            "current_vendor_score": 78,
            "prior_vendor_score": 76,
            "vendor_score_delta": 2,
            "trend_band": _score_trend_band(2),
            "repeat_event_count": 2,
            "high_risk_event_count": 1,
            "capa_linked_event_count": 0,
            "latest_event_type": "transport_timing_variance",
            "primary_site": "St Francis",
            "linked_capa_id": "",
            "executive_priority": _executive_priority(78, 2, 1, 0),
            "recommended_action": "Continue manager follow-up and monitor transport timing variance for recurrence.",
        },
        {
            "vendor_name": "ClearView Endoscopy",
            "vendor_category": "Flexible Scope Accessories",
            "current_vendor_score": 88,
            "prior_vendor_score": 82,
            "vendor_score_delta": 6,
            "trend_band": _score_trend_band(6),
            "repeat_event_count": 1,
            "high_risk_event_count": 0,
            "capa_linked_event_count": 0,
            "latest_event_type": "documentation_response_improved",
            "primary_site": "St Mary",
            "linked_capa_id": "",
            "executive_priority": _executive_priority(88, 1, 0, 0),
            "recommended_action": "Maintain routine monitoring and document improved response trend.",
        },
    ]


@router.get("/health")
def vendor_trend_intelligence_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "module": "vendor_trend_intelligence",
        "version": "v1",
        "product_phase": "v1.2",
        "timestamp": _utc_now(),
        "capabilities": [
            "vendor_trend_summary",
            "vendor_score_movement",
            "repeat_event_detection",
            "high_risk_vendor_detection",
            "capa_linkage_visibility",
            "csv_export",
            "executive_vendor_review_guidance",
        ],
    }


@router.get("/summary")
def vendor_trend_intelligence_summary() -> Dict[str, Any]:
    items = _vendor_trend_items()

    average_vendor_score = round(sum(item["current_vendor_score"] for item in items) / len(items))
    prior_average_vendor_score = round(sum(item["prior_vendor_score"] for item in items) / len(items))
    vendor_score_delta = average_vendor_score - prior_average_vendor_score

    repeat_event_vendor_count = sum(1 for item in items if item["repeat_event_count"] >= 2)
    high_risk_vendor_count = sum(1 for item in items if item["high_risk_event_count"] >= 2)
    capa_linked_vendor_count = sum(1 for item in items if item["capa_linked_event_count"] > 0)
    executive_review_count = sum(
        1 for item in items if item["executive_priority"] == "executive_review"
    )
    leadership_watch_count = sum(
        1 for item in items if item["executive_priority"] == "leadership_watch"
    )

    if executive_review_count > 0:
        vendor_trend_status = "executive_action_required"
    elif leadership_watch_count > 0 or vendor_score_delta < 0:
        vendor_trend_status = "leadership_watch"
    else:
        vendor_trend_status = "controlled"

    return {
        "status": "success",
        "module": "vendor_trend_intelligence",
        "version": "v1",
        "product_phase": "v1.2",
        "timestamp": _utc_now(),
        "trend_window": "current_month_vs_prior_month",
        "vendor_trend_status": vendor_trend_status,
        "average_vendor_score": average_vendor_score,
        "prior_average_vendor_score": prior_average_vendor_score,
        "vendor_score_delta": vendor_score_delta,
        "vendor_score_trend_band": _score_trend_band(vendor_score_delta),
        "repeat_event_vendor_count": repeat_event_vendor_count,
        "high_risk_vendor_count": high_risk_vendor_count,
        "capa_linked_vendor_count": capa_linked_vendor_count,
        "executive_review_count": executive_review_count,
        "leadership_watch_count": leadership_watch_count,
        "vendor_trend_items": items,
        "executive_recommendations": [
            "Review vendors assigned to executive_review before routine vendor governance discussion.",
            "Prioritize vendors with worsening score movement, repeat events, and CAPA-linked defects.",
            "Use vendor_score_delta and repeat_event_vendor_count as monthly vendor governance indicators.",
            "Link repeat vendor events to CAPA governance and contract performance review.",
        ],
        "next_actions": [
            {
                "priority": "high",
                "action": "Create Vendor Trend Intelligence frontend cards.",
                "rationale": "Make vendor score movement, repeat events, and CAPA linkage visible to executive users.",
            },
            {
                "priority": "high",
                "action": "Add vendor trend metrics to Power BI export model.",
                "rationale": "Enable monthly vendor performance trend reporting and executive business review readiness.",
            },
            {
                "priority": "medium",
                "action": "Connect Vendor Trend Intelligence to live vendor events in a future milestone.",
                "rationale": "Move from deterministic trend examples to database-backed vendor governance intelligence.",
            },
        ],
    }


@router.get("/export.csv", response_class=PlainTextResponse)
def vendor_trend_intelligence_csv_export() -> PlainTextResponse:
    items = _vendor_trend_items()
    output = StringIO()

    fieldnames = [
        "vendor_name",
        "vendor_category",
        "current_vendor_score",
        "prior_vendor_score",
        "vendor_score_delta",
        "trend_band",
        "repeat_event_count",
        "high_risk_event_count",
        "capa_linked_event_count",
        "latest_event_type",
        "primary_site",
        "linked_capa_id",
        "executive_priority",
        "recommended_action",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(items)

    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; filename=lumenai_v1_2_vendor_trend_intelligence.csv"
            )
        },
    )
