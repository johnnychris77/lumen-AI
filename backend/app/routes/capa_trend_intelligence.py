from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List
import csv

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(
    prefix="/api/v1-2/capa/trend-intelligence",
    tags=["v1.2 CAPA Trend Intelligence"],
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trend_band(delta: int) -> str:
    if delta >= 10:
        return "worsening"
    if delta >= 3:
        return "watch"
    if delta <= -5:
        return "improving"
    return "stable"


def _executive_priority(risk_score: int, overdue_days: int, recurrence_count: int) -> str:
    if risk_score >= 85 or overdue_days >= 15 or recurrence_count >= 3:
        return "executive_review"
    if risk_score >= 70 or overdue_days > 0 or recurrence_count >= 2:
        return "leadership_watch"
    if risk_score >= 55:
        return "manager_follow_up"
    return "routine_monitoring"


def _trend_items() -> List[Dict[str, Any]]:
    return [
        {
            "capa_id": "CAPA-2026-001",
            "title": "Repeat vendor tray quality defects",
            "owner": "Quality Governance",
            "site": "Market",
            "current_risk_score": 88,
            "prior_risk_score": 76,
            "risk_score_delta": 12,
            "trend_band": _trend_band(12),
            "days_open": 42,
            "overdue_days": 16,
            "recurrence_count": 4,
            "linked_vendor": "OrthoTech Instruments",
            "executive_priority": _executive_priority(88, 16, 4),
            "recommended_action": "Escalate to executive CAPA review and require vendor corrective action linkage.",
        },
        {
            "capa_id": "CAPA-2026-002",
            "title": "Sterile processing documentation gap",
            "owner": "SPD Operations",
            "site": "St Mary",
            "current_risk_score": 74,
            "prior_risk_score": 70,
            "risk_score_delta": 4,
            "trend_band": _trend_band(4),
            "days_open": 28,
            "overdue_days": 3,
            "recurrence_count": 2,
            "linked_vendor": "",
            "executive_priority": _executive_priority(74, 3, 2),
            "recommended_action": "Review owner action plan and verify evidence of containment.",
        },
        {
            "capa_id": "CAPA-2026-003",
            "title": "Inspection finding recurrence",
            "owner": "Inspection Governance",
            "site": "ORC",
            "current_risk_score": 69,
            "prior_risk_score": 72,
            "risk_score_delta": -3,
            "trend_band": _trend_band(-3),
            "days_open": 18,
            "overdue_days": 0,
            "recurrence_count": 2,
            "linked_vendor": "Precision Spine Systems",
            "executive_priority": _executive_priority(69, 0, 2),
            "recommended_action": "Continue monitoring trend and link inspection recurrence to CAPA closure evidence.",
        },
        {
            "capa_id": "CAPA-2026-004",
            "title": "Policy review completion delay",
            "owner": "Regulatory Readiness",
            "site": "Market",
            "current_risk_score": 52,
            "prior_risk_score": 60,
            "risk_score_delta": -8,
            "trend_band": _trend_band(-8),
            "days_open": 12,
            "overdue_days": 0,
            "recurrence_count": 1,
            "linked_vendor": "",
            "executive_priority": _executive_priority(52, 0, 1),
            "recommended_action": "Maintain routine monitoring and verify policy approval milestone.",
        },
    ]


@router.get("/health")
def capa_trend_intelligence_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "module": "capa_trend_intelligence",
        "version": "v1",
        "product_phase": "v1.2",
        "timestamp": _utc_now(),
        "capabilities": [
            "capa_trend_summary",
            "risk_score_movement",
            "recurrence_detection",
            "aging_risk_detection",
            "owner_workload_signal",
            "csv_export",
            "executive_escalation_guidance",
        ],
    }


@router.get("/summary")
def capa_trend_intelligence_summary() -> Dict[str, Any]:
    items = _trend_items()

    average_risk_score = round(sum(item["current_risk_score"] for item in items) / len(items))
    prior_average_risk_score = round(sum(item["prior_risk_score"] for item in items) / len(items))
    risk_score_delta = average_risk_score - prior_average_risk_score

    overdue_count = sum(1 for item in items if item["overdue_days"] > 0)
    prior_overdue_count = 1
    overdue_delta = overdue_count - prior_overdue_count

    recurrence_count = sum(1 for item in items if item["recurrence_count"] >= 2)
    aging_risk_count = sum(1 for item in items if item["days_open"] >= 30 or item["overdue_days"] > 0)
    owner_workload_risk_count = sum(
        1 for item in items if item["owner"] in {"Quality Governance", "SPD Operations"}
    )
    executive_review_count = sum(
        1 for item in items if item["executive_priority"] == "executive_review"
    )
    leadership_watch_count = sum(
        1 for item in items if item["executive_priority"] == "leadership_watch"
    )

    if executive_review_count > 0:
        trend_status = "executive_action_required"
    elif leadership_watch_count > 0 or risk_score_delta > 0:
        trend_status = "leadership_watch"
    else:
        trend_status = "controlled"

    return {
        "status": "success",
        "module": "capa_trend_intelligence",
        "version": "v1",
        "product_phase": "v1.2",
        "timestamp": _utc_now(),
        "trend_window": "current_month_vs_prior_month",
        "capa_trend_status": trend_status,
        "average_risk_score": average_risk_score,
        "prior_average_risk_score": prior_average_risk_score,
        "risk_score_delta": risk_score_delta,
        "risk_trend_band": _trend_band(risk_score_delta),
        "overdue_count": overdue_count,
        "prior_overdue_count": prior_overdue_count,
        "overdue_delta": overdue_delta,
        "overdue_trend": _trend_band(overdue_delta),
        "recurrence_count": recurrence_count,
        "aging_risk_count": aging_risk_count,
        "owner_workload_risk_count": owner_workload_risk_count,
        "executive_review_count": executive_review_count,
        "leadership_watch_count": leadership_watch_count,
        "trend_items": items,
        "executive_recommendations": [
            "Review executive_review CAPAs before routine CAPA governance discussion.",
            "Prioritize CAPAs with worsening risk_score_delta and recurring findings.",
            "Use overdue_delta and aging_risk_count as monthly executive dashboard signals.",
            "Link recurring vendor-related CAPAs to Vendor Performance governance.",
        ],
        "next_actions": [
            {
                "priority": "high",
                "action": "Create CAPA Trend Intelligence frontend cards.",
                "rationale": "Make CAPA risk movement and recurrence visible to executive users.",
            },
            {
                "priority": "high",
                "action": "Add CAPA trend metrics to Power BI export model.",
                "rationale": "Enable monthly trend reporting and board-ready CAPA analytics.",
            },
            {
                "priority": "medium",
                "action": "Connect CAPA trend intelligence to live CAPA records in a future milestone.",
                "rationale": "Move from deterministic trend examples to database-backed operational intelligence.",
            },
        ],
    }


@router.get("/export.csv", response_class=PlainTextResponse)
def capa_trend_intelligence_csv_export() -> PlainTextResponse:
    items = _trend_items()
    output = StringIO()

    fieldnames = [
        "capa_id",
        "title",
        "owner",
        "site",
        "current_risk_score",
        "prior_risk_score",
        "risk_score_delta",
        "trend_band",
        "days_open",
        "overdue_days",
        "recurrence_count",
        "linked_vendor",
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
                "attachment; filename=lumenai_v1_2_capa_trend_intelligence.csv"
            )
        },
    )
