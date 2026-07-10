"""v4.5 — Project Orbit, Section 7: Executive Surgical Operations Dashboard.

Composes `or_connect_service.executive_dashboard` (already real: case
readiness trend, delay causes, vendor performance, inspection turnaround,
repair impact, quality alerts, operational bottlenecks) with Digital Twin
risk and enterprise cross-facility comparison — nothing here recomputes
what Symphony/Digital Twin/Atlas already compute.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.services import atlas_dashboard_service, digital_twin_engine, or_connect_service, platform_org_service


def executive_surgical_operations(db: Session, tenant_id: str, *, facility_id: str = "", days: int = 30) -> dict:
    today = datetime.now(timezone.utc).date()
    dashboard_today = or_connect_service.dashboard_summary(db, tenant_id, target_date=today)
    executive = or_connect_service.executive_dashboard(db, tenant_id, days=days)

    twin_dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, facility_id, db)
    high_risk_twin_alerts = [a for a in twin_dashboard.open_alerts if a.severity in ("high", "critical")]

    facility = platform_org_service.facility_for_tenant(db, tenant_id)
    cross_facility_comparison = None
    if facility is not None:
        enterprise = atlas_dashboard_service.enterprise_dashboard(db, facility["system_id"])
        cross_facility_comparison = enterprise.get("facility_comparison")

    top_operational_risks = sorted(
        [{"risk_type": k, "count": v} for k, v in executive["delay_causes"].items()],
        key=lambda x: x["count"], reverse=True,
    )[:10]

    return {
        "date": today.isoformat(),
        "cases_today": dashboard_today["total_cases"],
        "readiness_pct": round(sum(c["readiness_score"] for c in dashboard_today["cases"]) / len(dashboard_today["cases"])) if dashboard_today["cases"] else None,
        "delayed_cases": len(dashboard_today["projected_delays"]),
        "inspection_holds": sum(1 for c in dashboard_today["cases"] if c["readiness_score"] < 100),
        "repair_holds": executive["repair_impact"]["cases_with_open_repairs"],
        "digital_twin_risk": {
            "utilization_pct": twin_dashboard.twin_state.utilization_pct,
            "high_risk_alert_count": len(high_risk_twin_alerts),
        },
        "enterprise_readiness": {
            "case_readiness_trend": executive["case_readiness_trend"],
        },
        "cross_facility_comparison": cross_facility_comparison,
        "top_operational_risks": top_operational_risks,
        "human_review_required": True,
        "disclaimer": or_connect_service.DISCLAIMER,
    }
