"""v3.3 — Project Insight, Section 3: Quality Trend Forecasting.

Historical series come from real rows (`InspectionFinding`, `Inspection`,
`SupervisorReview`) bucketed by day — the same "report 0, don't omit"
philosophy `finding_trend_service.py` already established — projected
forward via `insight_forecast_math.py`'s OLS trend, never a seeded mock.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.predictive_insight import (
    HORIZON_DAYS,
    METRIC_BLOOD,
    METRIC_BONE,
    METRIC_CORROSION,
    METRIC_COVERAGE_COMPLIANCE,
    METRIC_DAMAGE,
    METRIC_DEBRIS,
    METRIC_INSPECTION_THROUGHPUT,
    METRIC_RUST,
    METRIC_SUPERVISOR_WORKLOAD,
    QUALITY_TREND_METRICS,
    QualityTrendForecast,
)
from app.models.supervisor_review import SupervisorReview
from app.services.insight_forecast_math import (
    build_explainability_envelope,
    confidence_from_trend,
    confidence_interval,
    linear_trend,
    project_forward,
)
from app.services.insight_forecast_math import trend_direction as _trend_direction

_FINDING_METRICS = {METRIC_BLOOD, METRIC_BONE, METRIC_DEBRIS, METRIC_RUST}
_DAMAGE_FINDING_TYPES = {"crack", "wear", "pitting", "missing_component", "insulation_damage"}
_SERIES_LOOKBACK_DAYS = 90


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _daily_bucket_labels(lookback_days: int) -> list[str]:
    today = datetime.now(timezone.utc).date()
    return [(today - timedelta(days=d)).isoformat() for d in range(lookback_days - 1, -1, -1)]


def _daily_series_for_metric(db: Session, tenant_id: str, metric: str) -> tuple[list[float], list[str]]:
    since = datetime.now(timezone.utc) - timedelta(days=_SERIES_LOOKBACK_DAYS)
    labels = _daily_bucket_labels(_SERIES_LOOKBACK_DAYS)
    counts = dict.fromkeys(labels, 0.0)

    if metric in _FINDING_METRICS or metric == METRIC_CORROSION or metric == METRIC_DAMAGE:
        finding_types = _DAMAGE_FINDING_TYPES if metric == METRIC_DAMAGE else {metric}
        rows = (
            db.query(InspectionFinding)
            .filter(InspectionFinding.tenant_id == tenant_id, InspectionFinding.created_at >= since, InspectionFinding.finding_type.in_(finding_types))
            .all()
        )
        for r in rows:
            label = r.created_at.date().isoformat()
            if label in counts:
                counts[label] += 1
        return [counts[label] for label in labels], labels

    if metric == METRIC_COVERAGE_COMPLIANCE:
        rows = (
            db.query(Inspection)
            .filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since, Inspection.coverage_pct.isnot(None))
            .all()
        )
        daily_values: dict[str, list[float]] = {label: [] for label in labels}
        for r in rows:
            label = r.created_at.date().isoformat()
            if label in daily_values:
                daily_values[label].append(r.coverage_pct)
        series = [sum(v) / len(v) if v else None for v in daily_values.values()]
        # Carry the last known value forward for days with no inspections,
        # rather than fabricating a 0% compliance day that never happened.
        last_known = 100.0
        filled = []
        for v in series:
            if v is None:
                filled.append(last_known)
            else:
                last_known = v
                filled.append(v)
        return filled, labels

    if metric == METRIC_SUPERVISOR_WORKLOAD:
        rows = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.created_at >= since).all()
        for r in rows:
            label = r.created_at.date().isoformat()
            if label in counts:
                counts[label] += 1
        return [counts[label] for label in labels], labels

    if metric == METRIC_INSPECTION_THROUGHPUT:
        rows = db.query(Inspection).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since).all()
        for r in rows:
            label = r.created_at.date().isoformat()
            if label in counts:
                counts[label] += 1
        return [counts[label] for label in labels], labels

    raise ValueError(f"metric must be one of {QUALITY_TREND_METRICS}")


def forecast_quality_trend(db: Session, tenant_id: str, *, metric: str, horizon: str) -> dict:
    if metric not in QUALITY_TREND_METRICS:
        raise ValueError(f"metric must be one of {QUALITY_TREND_METRICS}")
    if horizon not in HORIZON_DAYS:
        raise ValueError(f"horizon must be one of {list(HORIZON_DAYS)}")

    series, labels = _daily_series_for_metric(db, tenant_id, metric)
    trend = linear_trend(series)
    steps_ahead = HORIZON_DAYS[horizon]
    forecast_value = project_forward(trend, steps_ahead)
    confidence = confidence_from_trend(trend)
    low, high = confidence_interval(forecast_value, trend) if forecast_value is not None else (None, None)
    direction = _trend_direction(trend)

    recent_avg = round(sum(series[-14:]) / len(series[-14:]), 3) if series else None
    prior_avg = round(sum(series[-28:-14]) / len(series[-28:-14]), 3) if len(series) >= 28 else None

    limitations = []
    if not trend["sufficient_data"]:
        limitations.append(f"Fewer than {5} data points available — trend is not statistically meaningful yet.")
    if all(v == 0 for v in series):
        limitations.append("No recorded activity for this metric in the lookback window.")

    envelope = build_explainability_envelope(
        data_sources=["InspectionFinding", "Inspection", "SupervisorReview"],
        time_horizon=horizon, confidence_level=confidence,
        contributing_factors=[
            {"factor": "sample_size", "value": trend["sample_size"], "signal": "sufficient" if trend["sufficient_data"] else "insufficient"},
            {"factor": "fit_quality_r_squared", "value": trend["r_squared"], "signal": "n/a" if trend["r_squared"] is None else ("strong" if trend["r_squared"] >= 0.5 else "weak")},
        ],
        historical_comparison={"recent_14d_avg": recent_avg, "prior_14d_avg": prior_avg},
        known_limitations=limitations,
    )

    row = QualityTrendForecast(
        tenant_id=tenant_id, metric=metric, horizon=horizon,
        historical_series_json=json.dumps(list(zip(labels[-30:], series[-30:]))),
        forecast_value=forecast_value, confidence_low=low, confidence_high=high, confidence_level=confidence,
        trend_direction=direction,
        data_sources_json=json.dumps(envelope["data_sources"]),
        contributing_factors_json=json.dumps(envelope["contributing_factors"]),
        historical_comparison_json=json.dumps(envelope["historical_comparison"]),
        known_limitations_json=json.dumps(envelope["known_limitations"]),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _row_to_dict(row)
    result["historical_series"] = list(zip(labels[-30:], series[-30:]))
    result["data_sources"] = envelope["data_sources"]
    result["contributing_factors"] = envelope["contributing_factors"]
    result["historical_comparison"] = envelope["historical_comparison"]
    result["known_limitations"] = envelope["known_limitations"]
    return result


def generate_all_quality_trend_forecasts(db: Session, tenant_id: str, *, horizon: str = "30_day") -> list[dict]:
    return [forecast_quality_trend(db, tenant_id, metric=m, horizon=horizon) for m in QUALITY_TREND_METRICS]


def list_quality_trend_forecasts(db: Session, tenant_id: str, *, metric: str = "", horizon: str = "") -> list[dict]:
    q = db.query(QualityTrendForecast).filter(QualityTrendForecast.tenant_id == tenant_id)
    if metric:
        q = q.filter(QualityTrendForecast.metric == metric)
    if horizon:
        q = q.filter(QualityTrendForecast.horizon == horizon)
    rows = q.order_by(QualityTrendForecast.id.desc()).limit(50).all()
    return [_row_to_dict(r) for r in rows]
