"""v3.3 — Project Insight, Section 1: Predictive Intelligence Engine.

The genuinely new piece this sprint adds: a single orchestrator that ties
together every predictive signal already computed elsewhere in this
codebase — instrument failure prediction (P7), quality forecasting (P22),
finding trends (v1.5), competency opportunities (Guardian v2.9) — plus
Insight's own quality-trend, operational, instrument-lifecycle, and
education forecasts, into one coherent "predictive insight" rather than a
pile of separate reactive reports. Every section here calls an existing
service; nothing is recomputed a second time.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.predictive_insight import DISCLAIMER
from app.services import (
    insight_education_forecast_service,
    insight_instrument_forecast_service,
    insight_operational_forecast_service,
    insight_quality_trend_service,
)
from app.services.digital_quality_twin_service import get_forecasts as get_quality_forecasts
from app.services.prediction_engine import compute_predictive_dashboard


def generate_predictive_intelligence(db: Session, tenant_id: str, *, horizon: str = "30_day") -> dict:
    quality_trends = insight_quality_trend_service.generate_all_quality_trend_forecasts(db, tenant_id, horizon=horizon)
    operational = insight_operational_forecast_service.generate_all_operational_forecasts(db, tenant_id, horizon=horizon)
    instrument_lifecycle = insight_instrument_forecast_service.generate_lifecycle_forecasts_for_tenant(db, tenant_id)
    education = insight_education_forecast_service.generate_predictive_education_signals(db, tenant_id)

    existing_failure_dashboard = compute_predictive_dashboard(tenant_id, db=db).model_dump()
    existing_quality_forecasts = get_quality_forecasts(db, tenant_id)

    adverse_quality_trends = [
        t for t in quality_trends
        if (t["trend_direction"] == "increasing" and t["metric"] not in ("coverage_compliance",))
        or (t["trend_direction"] == "decreasing" and t["metric"] == "coverage_compliance")
    ]
    elevated_lifecycle_risks = [f for f in instrument_lifecycle if f["lifecycle_risk_tier"] in ("high", "critical")]

    return {
        "tenant_id": tenant_id,
        "horizon": horizon,
        "quality_trend_forecasts": quality_trends,
        "operational_forecasts": operational,
        "instrument_lifecycle_forecasts": instrument_lifecycle,
        "predictive_education": education,
        "existing_instrument_failure_dashboard": existing_failure_dashboard,
        "existing_quality_forecasts": existing_quality_forecasts,
        "summary": {
            "adverse_quality_trend_count": len(adverse_quality_trends),
            "elevated_instrument_lifecycle_risk_count": len(elevated_lifecycle_risks),
            "new_education_signal_count": len(education["new_signals"]),
        },
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def build_forecast_dashboard(intelligence: dict) -> dict:
    """Section 7: /forecast — maps the full Section 1 intelligence payload
    onto the six named displays the sprint asks for, each with its own
    confidence indicator, rather than handing the dashboard the entire
    raw payload."""
    quality_trends = intelligence["quality_trend_forecasts"]
    operational = {o["forecast_type"]: o for o in intelligence["operational_forecasts"]}
    lifecycle = intelligence["instrument_lifecycle_forecasts"]

    def _avg_confidence(items: list[dict]) -> float | None:
        levels = [i["confidence_level"] for i in items if i.get("confidence_level") is not None]
        return round(sum(levels) / len(levels), 3) if levels else None

    return {
        "tenant_id": intelligence["tenant_id"],
        "horizon": intelligence["horizon"],
        "enterprise_quality_forecast": {
            "metrics": quality_trends,
            "confidence": _avg_confidence(quality_trends),
        },
        "risk_forecast": {
            "instrument_lifecycle": lifecycle,
            "elevated_risk_count": intelligence["summary"]["elevated_instrument_lifecycle_risk_count"],
            "confidence": _avg_confidence(lifecycle),
        },
        "repair_forecast": {
            "instrument_repair_likelihoods": [
                {"instrument_type": f["instrument_type"], "repair_likelihood": f["repair_likelihood"], "repair_recurrence_likelihood": f["repair_recurrence_likelihood"]}
                for f in lifecycle
            ],
            "repair_backlog_forecast": operational.get("repair_backlog"),
            "confidence": _avg_confidence(lifecycle),
        },
        "instrument_health_forecast": {
            "health_score_trajectories": [
                {"instrument_type": f["instrument_type"], "health_score_trajectory": f["health_score_trajectory"], "lifecycle_risk_tier": f["lifecycle_risk_tier"]}
                for f in lifecycle
            ],
            "confidence": _avg_confidence(lifecycle),
        },
        "inspection_volume_forecast": {
            "inspection_workload": operational.get("inspection_workload"),
            "peak_inspection_periods": operational.get("peak_inspection_periods"),
            "confidence": operational.get("inspection_workload", {}).get("confidence_level"),
        },
        "education_forecast": intelligence["predictive_education"],
        "human_review_required": True,
        "disclaimer": intelligence["disclaimer"],
    }
