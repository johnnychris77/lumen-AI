"""v2.4 — Instrument Health Forecast (Clinical Memory, Section 5).

Extends the existing Predictive Instrument Intelligence
(`app/services/instrument_intelligence.instrument_timeline` — risk trend,
remaining-useful-life estimate) with the condition/repair trend already
computed by `instrument_condition_service` and an honest confidence interval
that widens as the sample size shrinks, rather than a fabricated fixed band.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.instrument_intelligence import instrument_timeline

# Wider band with fewer inspections — small samples get less claimed precision,
# never a fixed-width interval regardless of how little history exists.
_MARGIN_BY_SAMPLE_SIZE = ((8, 5), (4, 12), (2, 20))


def _confidence_margin(sample_size: int) -> int | None:
    for min_count, margin in _MARGIN_BY_SAMPLE_SIZE:
        if sample_size >= min_count:
            return margin
    return None


def forecast_instrument_health(db: Session, tenant_id: str, instrument_identity: str, condition: dict) -> dict:
    identifier = instrument_identity.split(":", 1)[1] if ":" in instrument_identity else instrument_identity
    base = instrument_timeline(db, identifier, tenant_id)
    prediction = base["prediction"]

    sample_size = condition["inspection_count"]
    margin = _confidence_margin(sample_size)
    latest_score = prediction["latest_risk_score"]
    confidence_interval = (
        {"low": max(0, latest_score - margin), "high": min(100, latest_score + margin)}
        if latest_score is not None and margin is not None else None
    )

    if condition["repair_count"] >= 2:
        repair_trend = "recurring"
    elif condition["repair_count"] == 1:
        repair_trend = "occurred_once"
    else:
        repair_trend = "none"

    return {
        "condition_trend": condition["condition_trend"],
        "failure_risk_trend": prediction["risk_trend"],
        "repair_trend": repair_trend,
        "estimated_remaining_useful_life": prediction["estimated_remaining_life"],
        "confidence_interval": confidence_interval,
        "sample_size": sample_size,
        "basis": prediction["note"],
        "human_review_required": True,
    }
