"""v3.3 — Project Insight: shared trend-projection math and explainability envelope.

One deterministic linear-trend implementation, shared by every Insight
forecast service (quality trend, operational, instrument lifecycle) so
"forecast" always means the same thing across sections: an ordinary-
least-squares fit over real historical bucketed counts, extrapolated
forward. No seeded randomness anywhere in this module — confidence comes
from sample size and residual spread, exactly the non-fabricated idiom
`sentinel_ai_health_service.py::_detect_drift` already established
(insufficient data -> an explicit limitation, never a fabricated number).
"""
from __future__ import annotations

from datetime import datetime, timezone

MIN_POINTS_FOR_TREND = 5


def as_naive_utc(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes even for DateTime(timezone=True)
    columns, while Postgres returns tz-aware ones — normalize to naive UTC
    so a row's timestamp can always be compared against a tz-aware "now"
    cutoff regardless of backend."""
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def linear_trend(series: list[float]) -> dict:
    """Ordinary least squares over (index, value) pairs.

    Returns {"slope", "intercept", "r_squared", "residual_stdev",
    "sufficient_data"}. `sufficient_data` is False (and the trend fields
    are None) when there are fewer than MIN_POINTS_FOR_TREND points —
    callers must not fabricate a trend from too little history.
    """
    n = len(series)
    if n < MIN_POINTS_FOR_TREND:
        return {"slope": None, "intercept": None, "r_squared": None, "residual_stdev": None, "mean_y": None, "sufficient_data": False, "sample_size": n}

    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(series) / n
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, series))
    ss_xx = sum((x - mean_x) ** 2 for x in xs)

    if ss_xx == 0:
        slope, intercept = 0.0, mean_y
    else:
        slope = ss_xy / ss_xx
        intercept = mean_y - slope * mean_x

    predicted = [intercept + slope * x for x in xs]
    residuals = [y - p for y, p in zip(series, predicted)]
    ss_res = sum(r ** 2 for r in residuals)
    ss_tot = sum((y - mean_y) ** 2 for y in series)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    residual_stdev = (ss_res / n) ** 0.5

    return {
        "slope": slope, "intercept": intercept, "r_squared": round(max(0.0, r_squared), 3),
        "residual_stdev": residual_stdev, "mean_y": mean_y, "sufficient_data": True, "sample_size": n,
    }


def project_forward(trend: dict, steps_ahead: int) -> float | None:
    if not trend["sufficient_data"]:
        return None
    n = trend["sample_size"]
    return trend["intercept"] + trend["slope"] * (n - 1 + steps_ahead)


def confidence_from_trend(trend: dict) -> float:
    """Confidence grows with sample size and fit quality (r_squared) —
    never a random draw. Capped at 0.95 (a forecast is never certain)."""
    if not trend["sufficient_data"]:
        return 0.0
    sample_component = min(1.0, trend["sample_size"] / 30)
    fit_component = trend["r_squared"]
    return round(min(0.95, 0.2 + 0.4 * sample_component + 0.4 * fit_component), 3)


def confidence_interval(forecast_value: float, trend: dict, *, z: float = 1.28) -> tuple[float, float]:
    """~80% interval (z=1.28) around the point forecast, widened by the
    trend's residual spread — real dispersion, not an arbitrary band."""
    if not trend["sufficient_data"] or forecast_value is None:
        return (None, None)
    margin = z * trend["residual_stdev"]
    return (round(forecast_value - margin, 3), round(forecast_value + margin, 3))


def trend_direction(trend: dict, *, stability_threshold: float = 0.05) -> str:
    """Direction is based on the *total* fitted change across the observed
    window, relative to the series' own mean — not the per-step slope
    normalized by the OLS intercept, which is a poor reference point for a
    sparse or non-stationary series (the intercept is only the fitted
    value at x=0, not representative of the series' overall scale)."""
    if not trend["sufficient_data"]:
        return "stable"
    total_change = trend["slope"] * (trend["sample_size"] - 1)
    relative_change = total_change / max(1.0, abs(trend["mean_y"]))
    if relative_change > stability_threshold:
        return "increasing"
    if relative_change < -stability_threshold:
        return "decreasing"
    return "stable"


def build_explainability_envelope(
    *, data_sources: list[str], time_horizon: str, confidence_level: float,
    contributing_factors: list[dict], historical_comparison: dict, known_limitations: list[str],
) -> dict:
    """Section 10: the shape every Insight forecast response guarantees."""
    return {
        "data_sources": data_sources,
        "time_horizon": time_horizon,
        "confidence_level": confidence_level,
        "contributing_factors": contributing_factors,
        "historical_comparison": historical_comparison,
        "known_limitations": known_limitations,
    }
