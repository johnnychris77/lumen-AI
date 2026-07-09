"""v3.3 — Project Insight, Sections 2 & 6: Instrument Failure Forecasting
& Predictive Digital Twin Analytics.

Operates at the `instrument_type` level (the field already used throughout
this codebase — `Inspection.instrument_type`), extending rather than
duplicating two existing engines:

  * `app/services/prediction_engine.py` (P7) already forecasts a *named*
    instrument's failure probability from `CVInferenceRecord` history.
    This module adds what P7 doesn't: corrosion-progression and
    recurring-damage *trend* scoring and removal-from-service likelihood,
    aggregated across every instrument of a type from real `Inspection`/
    `InspectionFinding`/`RepairRequest` rows (not `CVInferenceRecord`,
    which this environment may not have populated).
  * `app/services/digital_quality_twin_service.py::get_forecasts` (P22)
    already forecasts a tenant's overall quality score at 30/60/90-day
    horizons. This module calls it for the baseline trajectory and adds a
    7-day and rolling-annual point (Section 6 asks for a wider horizon
    set) plus retirement likelihood and a lifecycle risk tier, which P22
    does not compute.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.inspection_finding import InspectionFinding
from app.models.or_connect import RepairRequest
from app.models.predictive_insight import LIFECYCLE_RISK_TIERS, InstrumentLifecycleForecast
from app.services.digital_quality_twin_service import get_forecasts as get_quality_forecasts
from app.services.insight_forecast_math import as_naive_utc

_LOOKBACK_DAYS = 90
_RECENT_WINDOW_DAYS = 30
_DAMAGE_FINDING_TYPES = {"crack", "wear", "pitting", "missing_component", "insulation_damage"}


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _trend_score(recent_count: float, prior_count: float) -> float:
    """50 = stable; >50 = worsening (recent higher than prior); <50 = improving."""
    if prior_count == 0 and recent_count == 0:
        return 50.0
    pct_change = (recent_count - prior_count) / max(1.0, prior_count) * 100
    return round(min(100.0, max(0.0, 50.0 + pct_change)), 1)


def _wald_interval(p: float, n: int, *, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (None, None)
    margin = z * math.sqrt(max(0.0, p * (1 - p)) / n)
    return (round(max(0.0, p - margin), 3), round(min(1.0, p + margin), 3))


def _lifecycle_risk_tier(retirement_likelihood: float) -> str:
    if retirement_likelihood >= 0.75:
        return LIFECYCLE_RISK_TIERS[3]  # critical
    if retirement_likelihood >= 0.5:
        return LIFECYCLE_RISK_TIERS[2]  # high
    if retirement_likelihood >= 0.25:
        return LIFECYCLE_RISK_TIERS[1]  # moderate
    return LIFECYCLE_RISK_TIERS[0]  # low


def _health_score_trajectory(db: Session, tenant_id: str) -> list[dict]:
    """Extends P22's 30/60/90-day QualityForecast with 7-day and
    rolling-annual points via linear extrapolation of the same trajectory."""
    base_forecasts = sorted(get_quality_forecasts(db, tenant_id), key=lambda f: f["forecast_horizon_days"])
    if len(base_forecasts) < 2:
        return [{"horizon_days": f["forecast_horizon_days"], "projected_quality_score": f["projected_quality_score"]} for f in base_forecasts]

    first, last = base_forecasts[0], base_forecasts[-1]
    slope_per_day = (last["projected_quality_score"] - first["projected_quality_score"]) / max(1, last["forecast_horizon_days"] - first["forecast_horizon_days"])

    def _project(days: int) -> float:
        return round(max(0.0, min(1.0, first["projected_quality_score"] + slope_per_day * (days - first["forecast_horizon_days"]))), 3)

    trajectory = [{"horizon_days": 7, "projected_quality_score": _project(7)}]
    trajectory += [{"horizon_days": f["forecast_horizon_days"], "projected_quality_score": f["projected_quality_score"]} for f in base_forecasts]
    trajectory.append({"horizon_days": 365, "projected_quality_score": _project(365)})
    return trajectory


def forecast_instrument_lifecycle(db: Session, tenant_id: str, instrument_type: str) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    # Naive UTC — every row's created_at is normalized to naive UTC via
    # as_naive_utc() before comparison, so this must match (see that
    # helper's docstring: SQLite/Postgres return created_at differently).
    recent_since = (datetime.now(timezone.utc) - timedelta(days=_RECENT_WINDOW_DAYS)).replace(tzinfo=None)

    inspections = (
        db.query(Inspection)
        .filter(Inspection.tenant_id == tenant_id, Inspection.instrument_type == instrument_type, Inspection.created_at >= since)
        .all()
    )
    n_inspections = len(inspections)
    inspection_ids = [i.id for i in inspections]

    findings = (
        db.query(InspectionFinding)
        .filter(InspectionFinding.tenant_id == tenant_id, InspectionFinding.instrument_type == instrument_type, InspectionFinding.created_at >= since)
        .all()
    )
    corrosion_recent = sum(1 for f in findings if f.finding_type == "corrosion" and as_naive_utc(f.created_at) >= recent_since)
    corrosion_prior = sum(1 for f in findings if f.finding_type == "corrosion" and as_naive_utc(f.created_at) < recent_since)
    damage_recent = sum(1 for f in findings if f.finding_type in _DAMAGE_FINDING_TYPES and as_naive_utc(f.created_at) >= recent_since)
    damage_prior = sum(1 for f in findings if f.finding_type in _DAMAGE_FINDING_TYPES and as_naive_utc(f.created_at) < recent_since)

    corrosion_progression_score = _trend_score(corrosion_recent, corrosion_prior)
    recurring_damage_score = _trend_score(damage_recent, damage_prior)

    repairs = db.query(RepairRequest).filter(RepairRequest.tenant_id == tenant_id, RepairRequest.inspection_id.in_(inspection_ids)).all() if inspection_ids else []
    repair_likelihood = round(len(repairs) / n_inspections, 3) if n_inspections else None
    # Recurrence: instruments that show up in RepairRequest more than once via distinct inspections is not
    # directly trackable without an instrument identity join, so recurrence is approximated as the
    # repair rate within the recent window alone.
    repairs_recent = sum(1 for r in repairs if as_naive_utc(r.created_at) >= recent_since)
    n_recent = sum(1 for i in inspections if as_naive_utc(i.created_at) >= recent_since) or 1
    repair_recurrence_likelihood = round(min(1.0, repairs_recent / n_recent), 3) if n_inspections else None

    removed_count = sum(1 for i in inspections if i.disposition == "REMOVE FROM SERVICE")
    removal_from_service_likelihood = round(removed_count / n_inspections, 3) if n_inspections else None

    retirement_likelihood = None
    confidence_low = confidence_high = None
    if n_inspections:
        retirement_likelihood = round(
            min(1.0, 0.5 * (removal_from_service_likelihood or 0) + 0.3 * (corrosion_progression_score / 100) + 0.2 * (recurring_damage_score / 100)),
            3,
        )
        confidence_low, confidence_high = _wald_interval(retirement_likelihood, n_inspections)

    lifecycle_risk_tier = _lifecycle_risk_tier(retirement_likelihood) if retirement_likelihood is not None else LIFECYCLE_RISK_TIERS[0]
    confidence_level = round(min(0.95, 0.2 + n_inspections * 0.05), 3) if n_inspections else 0.0

    limitations = []
    if n_inspections < 5:
        limitations.append(f"Only {n_inspections} inspections of this instrument type in the last {_LOOKBACK_DAYS} days — estimates are low-confidence.")
    if not repairs:
        limitations.append("No repair history on file for this instrument type in the lookback window.")

    evidence = [
        {"factor": "inspections_in_window", "value": n_inspections, "weight": 0.2, "signal": "sample_size"},
        {"factor": "corrosion_trend_recent_vs_prior", "value": f"{corrosion_recent} vs {corrosion_prior}", "weight": 0.25, "signal": "worsening" if corrosion_progression_score > 55 else ("improving" if corrosion_progression_score < 45 else "stable")},
        {"factor": "damage_trend_recent_vs_prior", "value": f"{damage_recent} vs {damage_prior}", "weight": 0.25, "signal": "worsening" if recurring_damage_score > 55 else ("improving" if recurring_damage_score < 45 else "stable")},
        {"factor": "removal_from_service_rate", "value": removal_from_service_likelihood, "weight": 0.3, "signal": "elevated" if (removal_from_service_likelihood or 0) > 0.1 else "normal"},
    ]

    health_trajectory = _health_score_trajectory(db, tenant_id)

    row = InstrumentLifecycleForecast(
        tenant_id=tenant_id, instrument_type=instrument_type,
        corrosion_progression_score=corrosion_progression_score, recurring_damage_score=recurring_damage_score,
        repair_recurrence_likelihood=repair_recurrence_likelihood, removal_from_service_likelihood=removal_from_service_likelihood,
        health_score_trajectory_json=json.dumps(health_trajectory), repair_likelihood=repair_likelihood,
        retirement_likelihood=retirement_likelihood, lifecycle_risk_tier=lifecycle_risk_tier,
        confidence_low=confidence_low, confidence_high=confidence_high, confidence_level=confidence_level,
        data_sources_json=json.dumps(["Inspection", "InspectionFinding", "RepairRequest", "QualityForecast"]),
        evidence_json=json.dumps(evidence), known_limitations_json=json.dumps(limitations),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = _row_to_dict(row)
    result["health_score_trajectory"] = health_trajectory
    result["evidence"] = evidence
    result["known_limitations"] = limitations
    result["data_sources"] = ["Inspection", "InspectionFinding", "RepairRequest", "QualityForecast"]
    return result


def generate_lifecycle_forecasts_for_tenant(db: Session, tenant_id: str) -> list[dict]:
    instrument_types = [
        row[0] for row in db.query(Inspection.instrument_type).filter(Inspection.tenant_id == tenant_id).distinct().all() if row[0]
    ]
    return [forecast_instrument_lifecycle(db, tenant_id, it) for it in instrument_types]


def list_lifecycle_forecasts(db: Session, tenant_id: str, *, instrument_type: str = "") -> list[dict]:
    q = db.query(InstrumentLifecycleForecast).filter(InstrumentLifecycleForecast.tenant_id == tenant_id)
    if instrument_type:
        q = q.filter(InstrumentLifecycleForecast.instrument_type == instrument_type)
    rows = q.order_by(InstrumentLifecycleForecast.id.desc()).limit(50).all()
    return [_row_to_dict(r) for r in rows]
