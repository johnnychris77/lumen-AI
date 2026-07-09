"""v3.3 — Project Insight, Section 5: Operational Forecasting.

Every forecast here is a real historical count series (Inspection,
SupervisorReview, RepairRequest) run through the same OLS trend
projection `insight_quality_trend_service.py` uses for quality metrics —
one shared math implementation (`insight_forecast_math.py`), never a
second forecasting method invented per operational concern.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.or_connect import REPAIR_PENDING, REPAIR_IN_PROGRESS, RepairRequest
from app.models.predictive_insight import (
    FORECAST_HIGH_RISK_PROCEDURE_PREP,
    FORECAST_INSPECTION_WORKLOAD,
    FORECAST_INSTRUMENT_AVAILABILITY,
    FORECAST_PEAK_INSPECTION_PERIODS,
    FORECAST_REPAIR_BACKLOG,
    FORECAST_SUPERVISOR_REVIEW_DEMAND,
    HORIZON_DAYS,
    OPERATIONAL_FORECAST_TYPES,
    OperationalForecast,
)
from app.models.supervisor_review import SupervisorReview
from app.services.insight_forecast_math import build_explainability_envelope, confidence_from_trend, linear_trend, project_forward

_SERIES_LOOKBACK_DAYS = 90
_OPEN_REPAIR_STATUSES = {REPAIR_PENDING, REPAIR_IN_PROGRESS}
_HIGH_RISK_SCORE_THRESHOLD = 60


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _daily_labels(lookback_days: int) -> list[str]:
    today = datetime.now(timezone.utc).date()
    return [(today - timedelta(days=d)).isoformat() for d in range(lookback_days - 1, -1, -1)]


def _daily_counts(rows, date_attr: str, labels: list[str]) -> list[float]:
    counts = dict.fromkeys(labels, 0.0)
    for r in rows:
        dt = getattr(r, date_attr)
        if dt is None:
            continue
        label = dt.date().isoformat()
        if label in counts:
            counts[label] += 1
    return [counts[label] for label in labels]


def _forecast_series(db: Session, tenant_id: str, forecast_type: str, horizon: str) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=_SERIES_LOOKBACK_DAYS)
    labels = _daily_labels(_SERIES_LOOKBACK_DAYS)
    data_sources = []
    detail: dict = {}

    if forecast_type == FORECAST_INSPECTION_WORKLOAD:
        rows = db.query(Inspection).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since).all()
        series = _daily_counts(rows, "created_at", labels)
        data_sources = ["Inspection"]

    elif forecast_type == FORECAST_SUPERVISOR_REVIEW_DEMAND:
        rows = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.created_at >= since).all()
        series = _daily_counts(rows, "created_at", labels)
        data_sources = ["SupervisorReview"]

    elif forecast_type == FORECAST_REPAIR_BACKLOG:
        rows = db.query(RepairRequest).filter(RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= since).all()
        opened = _daily_counts(rows, "created_at", labels)
        closed_rows = [r for r in rows if r.actual_return_date is not None]
        closed = _daily_counts(closed_rows, "actual_return_date", labels)
        backlog = []
        running = max(0, db.query(RepairRequest).filter(RepairRequest.tenant_id == tenant_id, RepairRequest.status.in_(_OPEN_REPAIR_STATUSES)).count() - sum(opened) + sum(closed))
        for o, c in zip(opened, closed):
            running = max(0.0, running + o - c)
            backlog.append(running)
        series = backlog
        data_sources = ["RepairRequest"]

    elif forecast_type == FORECAST_INSTRUMENT_AVAILABILITY:
        rows = db.query(Inspection).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since).all()
        daily_total: dict[str, int] = defaultdict(int)
        daily_unavailable: dict[str, int] = defaultdict(int)
        for r in rows:
            label = r.created_at.date().isoformat()
            if label in labels:
                daily_total[label] += 1
                if r.disposition in ("REPROCESS", "REMOVE FROM SERVICE"):
                    daily_unavailable[label] += 1
        series = [
            round(100 * (1 - daily_unavailable[label] / daily_total[label]), 2) if daily_total.get(label) else 100.0
            for label in labels
        ]
        data_sources = ["Inspection"]

    elif forecast_type == FORECAST_HIGH_RISK_PROCEDURE_PREP:
        rows = (
            db.query(Inspection)
            .filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since, Inspection.risk_score >= _HIGH_RISK_SCORE_THRESHOLD)
            .all()
        )
        series = _daily_counts(rows, "created_at", labels)
        data_sources = ["Inspection"]

    elif forecast_type == FORECAST_PEAK_INSPECTION_PERIODS:
        rows = db.query(Inspection).filter(Inspection.tenant_id == tenant_id, Inspection.created_at >= since).all()
        by_weekday: dict[int, list[int]] = defaultdict(list)
        daily_counts_map: dict[str, int] = defaultdict(int)
        for r in rows:
            label = r.created_at.date().isoformat()
            daily_counts_map[label] += 1
        for label in labels:
            weekday = datetime.fromisoformat(label).weekday()
            by_weekday[weekday].append(daily_counts_map.get(label, 0))
        weekday_avgs = {wd: (sum(vals) / len(vals) if vals else 0.0) for wd, vals in by_weekday.items()}
        peak_weekday = max(weekday_avgs, key=weekday_avgs.get) if weekday_avgs else None
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        detail = {
            "weekday_averages": {weekday_names[wd]: round(v, 2) for wd, v in weekday_avgs.items()},
            "peak_day_of_week": weekday_names[peak_weekday] if peak_weekday is not None else None,
        }
        series = [weekday_avgs.get(wd, 0.0) for wd in sorted(weekday_avgs)]
        data_sources = ["Inspection"]

    else:
        raise ValueError(f"forecast_type must be one of {OPERATIONAL_FORECAST_TYPES}")

    return {"series": series, "data_sources": data_sources, "detail": detail}


def forecast_operational(db: Session, tenant_id: str, *, forecast_type: str, horizon: str) -> dict:
    if forecast_type not in OPERATIONAL_FORECAST_TYPES:
        raise ValueError(f"forecast_type must be one of {OPERATIONAL_FORECAST_TYPES}")
    if horizon not in HORIZON_DAYS:
        raise ValueError(f"horizon must be one of {list(HORIZON_DAYS)}")

    built = _forecast_series(db, tenant_id, forecast_type, horizon)
    series = built["series"]

    if forecast_type == FORECAST_PEAK_INSPECTION_PERIODS:
        # A distributional pattern, not a forward point-value — no OLS projection needed.
        confidence = 0.6 if any(v > 0 for v in series) else 0.0
        forecast_value = None
        limitations = [] if any(v > 0 for v in series) else ["No inspection activity recorded in the lookback window."]
    else:
        trend = linear_trend(series)
        forecast_value = project_forward(trend, HORIZON_DAYS[horizon])
        confidence = confidence_from_trend(trend)
        limitations = [] if trend["sufficient_data"] else ["Fewer than 5 data points available — trend is not statistically meaningful yet."]

    envelope = build_explainability_envelope(
        data_sources=built["data_sources"], time_horizon=horizon, confidence_level=confidence,
        contributing_factors=[{"factor": "historical_window_days", "value": _SERIES_LOOKBACK_DAYS, "signal": "reference"}],
        historical_comparison={"recent_14d_avg": round(sum(series[-14:]) / len(series[-14:]), 3) if series else None},
        known_limitations=limitations,
    )

    row = OperationalForecast(
        tenant_id=tenant_id, forecast_type=forecast_type, horizon=horizon, forecast_value=forecast_value,
        forecast_detail_json=json.dumps(built["detail"]), confidence_level=confidence,
        data_sources_json=json.dumps(envelope["data_sources"]),
        contributing_factors_json=json.dumps(envelope["contributing_factors"]),
        known_limitations_json=json.dumps(envelope["known_limitations"]),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _row_to_dict(row)
    result["forecast_detail"] = built["detail"]
    result["data_sources"] = envelope["data_sources"]
    result["contributing_factors"] = envelope["contributing_factors"]
    result["historical_comparison"] = envelope["historical_comparison"]
    result["known_limitations"] = envelope["known_limitations"]
    return result


def generate_all_operational_forecasts(db: Session, tenant_id: str, *, horizon: str = "30_day") -> list[dict]:
    return [forecast_operational(db, tenant_id, forecast_type=t, horizon=horizon) for t in OPERATIONAL_FORECAST_TYPES]


def list_operational_forecasts(db: Session, tenant_id: str, *, forecast_type: str = "", horizon: str = "") -> list[dict]:
    q = db.query(OperationalForecast).filter(OperationalForecast.tenant_id == tenant_id)
    if forecast_type:
        q = q.filter(OperationalForecast.forecast_type == forecast_type)
    if horizon:
        q = q.filter(OperationalForecast.horizon == horizon)
    rows = q.order_by(OperationalForecast.id.desc()).limit(50).all()
    return [_row_to_dict(r) for r in rows]
