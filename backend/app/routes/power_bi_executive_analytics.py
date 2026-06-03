from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List
import csv

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(
    prefix="/api/v1-2/power-bi/executive-analytics",
    tags=["v1.2 Power BI Executive Analytics"],
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _executive_rows() -> List[Dict[str, Any]]:
    """
    Deterministic v1.2 Power BI-ready executive analytics dataset.

    This v1 endpoint intentionally uses stable demo-safe values so the API is
    portfolio-ready, testable, and predictable. Future v1.2 milestones can
    replace this with live database-backed monthly snapshots.
    """
    snapshot_month = "2026-06"

    return [
        {
            "snapshot_month": snapshot_month,
            "domain": "governance_intelligence",
            "metric_key": "governance_health_score",
            "metric_label": "Governance Health Score",
            "metric_value": 89,
            "metric_unit": "score",
            "status": "executive_ready",
            "risk_band": "controlled",
            "executive_priority": "routine_monitoring",
            "trend_direction": "stable",
            "power_bi_category": "Executive Governance",
            "recommended_action": "Maintain governance review cadence and continue monthly executive dashboard validation.",
        },
        {
            "snapshot_month": snapshot_month,
            "domain": "capa_predictive_risk",
            "metric_key": "average_risk_score",
            "metric_label": "Average CAPA Risk Score",
            "metric_value": 77,
            "metric_unit": "score",
            "status": "action_required",
            "risk_band": "high",
            "executive_priority": "leadership_watch",
            "trend_direction": "watch",
            "power_bi_category": "CAPA Risk",
            "recommended_action": "Review high-priority and overdue CAPAs during executive quality huddle.",
        },
        {
            "snapshot_month": snapshot_month,
            "domain": "capa_predictive_risk",
            "metric_key": "overdue_count",
            "metric_label": "Overdue CAPA Count",
            "metric_value": 1,
            "metric_unit": "count",
            "status": "action_required",
            "risk_band": "high",
            "executive_priority": "manager_follow_up",
            "trend_direction": "watch",
            "power_bi_category": "CAPA Risk",
            "recommended_action": "Escalate overdue CAPA owner follow-up and verify closure plan.",
        },
        {
            "snapshot_month": snapshot_month,
            "domain": "vendor_performance",
            "metric_key": "average_vendor_score",
            "metric_label": "Average Vendor Score",
            "metric_value": 71,
            "metric_unit": "score",
            "status": "action_required",
            "risk_band": "watch",
            "executive_priority": "leadership_watch",
            "trend_direction": "watch",
            "power_bi_category": "Vendor Performance",
            "recommended_action": "Review vendor watchlist and link repeat events to CAPA accountability.",
        },
        {
            "snapshot_month": snapshot_month,
            "domain": "vendor_performance",
            "metric_key": "high_risk_vendor_count",
            "metric_label": "High-Risk Vendor Count",
            "metric_value": 2,
            "metric_unit": "count",
            "status": "action_required",
            "risk_band": "high",
            "executive_priority": "executive_review",
            "trend_direction": "watch",
            "power_bi_category": "Vendor Performance",
            "recommended_action": "Prioritize high-risk vendors for executive vendor review.",
        },
        {
            "snapshot_month": snapshot_month,
            "domain": "vendor_performance",
            "metric_key": "capa_linked_vendor_count",
            "metric_label": "CAPA-Linked Vendor Count",
            "metric_value": 2,
            "metric_unit": "count",
            "status": "action_required",
            "risk_band": "high",
            "executive_priority": "executive_review",
            "trend_direction": "watch",
            "power_bi_category": "Vendor Performance",
            "recommended_action": "Track CAPA-linked vendor events through governance closure.",
        },
    ]


def _data_dictionary() -> List[Dict[str, str]]:
    return [
        {
            "field_name": "snapshot_month",
            "field_type": "string",
            "description": "Monthly reporting period for Power BI trend snapshots.",
            "power_bi_usage": "Date/month slicer and trend axis.",
        },
        {
            "field_name": "domain",
            "field_type": "string",
            "description": "Governance domain such as governance_intelligence, capa_predictive_risk, or vendor_performance.",
            "power_bi_usage": "Domain slicer and report grouping.",
        },
        {
            "field_name": "metric_key",
            "field_type": "string",
            "description": "Machine-readable metric identifier.",
            "power_bi_usage": "Metric mapping and semantic model key.",
        },
        {
            "field_name": "metric_label",
            "field_type": "string",
            "description": "Human-readable metric name.",
            "power_bi_usage": "Card title, table label, and tooltip display.",
        },
        {
            "field_name": "metric_value",
            "field_type": "number",
            "description": "Numeric metric value used for cards, charts, and thresholds.",
            "power_bi_usage": "Primary measure value.",
        },
        {
            "field_name": "metric_unit",
            "field_type": "string",
            "description": "Unit of measure such as score, count, percent, or days.",
            "power_bi_usage": "Measure formatting and tooltip context.",
        },
        {
            "field_name": "status",
            "field_type": "string",
            "description": "Executive status for the metric.",
            "power_bi_usage": "Conditional formatting and executive status filtering.",
        },
        {
            "field_name": "risk_band",
            "field_type": "string",
            "description": "Risk grouping such as controlled, watch, high, or critical.",
            "power_bi_usage": "Risk filtering, color rules, and heatmap grouping.",
        },
        {
            "field_name": "executive_priority",
            "field_type": "string",
            "description": "Leadership action priority assigned to the metric.",
            "power_bi_usage": "Executive action filters and prioritization tables.",
        },
        {
            "field_name": "trend_direction",
            "field_type": "string",
            "description": "Trend signal such as improving, stable, watch, or worsening.",
            "power_bi_usage": "Trend icons and monthly movement summaries.",
        },
        {
            "field_name": "power_bi_category",
            "field_type": "string",
            "description": "Power BI report category for dashboard navigation.",
            "power_bi_usage": "Report page grouping and visual segmentation.",
        },
        {
            "field_name": "recommended_action",
            "field_type": "string",
            "description": "Executive action guidance tied to the metric.",
            "power_bi_usage": "Executive summary table and action log.",
        },
    ]


@router.get("/health")
def power_bi_executive_analytics_health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "module": "power_bi_executive_analytics",
        "version": "v1",
        "product_phase": "v1.2",
        "timestamp": _utc_now(),
        "capabilities": [
            "power_bi_ready_executive_dataset",
            "unified_governance_metric_export",
            "capa_risk_power_bi_metrics",
            "vendor_performance_power_bi_metrics",
            "data_dictionary",
            "csv_export",
        ],
    }


@router.get("/summary")
def power_bi_executive_analytics_summary() -> Dict[str, Any]:
    rows = _executive_rows()

    action_required_count = sum(1 for row in rows if row["status"] == "action_required")
    executive_review_count = sum(1 for row in rows if row["executive_priority"] == "executive_review")
    high_risk_count = sum(1 for row in rows if row["risk_band"] == "high")

    return {
        "status": "success",
        "module": "power_bi_executive_analytics",
        "version": "v1",
        "product_phase": "v1.2",
        "timestamp": _utc_now(),
        "dataset_name": "lumenai_v1_2_executive_governance_power_bi_dataset",
        "row_count": len(rows),
        "domain_count": len({row["domain"] for row in rows}),
        "action_required_count": action_required_count,
        "executive_review_count": executive_review_count,
        "high_risk_count": high_risk_count,
        "power_bi_readiness_status": "ready",
        "available_exports": [
            "/api/v1-2/power-bi/executive-analytics/export.csv",
            "/api/v1-2/power-bi/executive-analytics/data-dictionary",
        ],
        "executive_recommendations": [
            "Use export.csv as the initial Power BI dataset for executive governance reporting.",
            "Use data-dictionary to map Power BI fields, slicers, cards, and conditional formatting.",
            "Trend snapshot_month over time as future live data or monthly exports are added.",
            "Use status, risk_band, and executive_priority as core executive dashboard filters.",
        ],
        "next_actions": [
            {
                "priority": "high",
                "action": "Create Power BI Executive Analytics frontend cards.",
                "rationale": "Make export readiness visible from the hosted frontend.",
            },
            {
                "priority": "high",
                "action": "Create evidence package for Power BI Executive Analytics API.",
                "rationale": "Lock API validation and export readiness evidence.",
            },
            {
                "priority": "medium",
                "action": "Add monthly snapshot support in a future v1.2 milestone.",
                "rationale": "Enable trend analytics for Power BI over time.",
            },
        ],
        "rows": rows,
    }


@router.get("/data-dictionary")
def power_bi_executive_analytics_data_dictionary() -> Dict[str, Any]:
    fields = _data_dictionary()
    return {
        "status": "success",
        "module": "power_bi_executive_analytics",
        "version": "v1",
        "product_phase": "v1.2",
        "timestamp": _utc_now(),
        "dictionary_name": "lumenai_v1_2_power_bi_executive_analytics_data_dictionary",
        "field_count": len(fields),
        "fields": fields,
    }


@router.get("/export.csv", response_class=PlainTextResponse)
def power_bi_executive_analytics_csv_export() -> PlainTextResponse:
    rows = _executive_rows()
    output = StringIO()

    fieldnames = [
        "snapshot_month",
        "domain",
        "metric_key",
        "metric_label",
        "metric_value",
        "metric_unit",
        "status",
        "risk_band",
        "executive_priority",
        "trend_direction",
        "power_bi_category",
        "recommended_action",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; filename=lumenai_v1_2_power_bi_executive_analytics.csv"
            )
        },
    )
