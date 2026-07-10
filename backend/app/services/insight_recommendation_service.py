"""v3.3 — Project Insight, Section 8: Predictive Recommendation Engine.

Every recommendation is derived from an already-generated forecast row
(quality trend, operational, instrument lifecycle, or education signal)
— never a bare suggestion. Each carries evidence, a numeric confidence
(copied from the source forecast, never re-fabricated), reasoning that
names the specific trigger, and a suggested action — matching this
sprint's own example shape ("Corrosion findings for orthopedic drill bits
are trending upward across two facilities. Review maintenance
practices."). Idempotent per title so re-running generation doesn't spam
duplicates for an already-open recommendation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.predictive_insight import (
    ADVERSE_WHEN_DECREASING,
    ADVERSE_WHEN_INCREASING,
    RECOMMENDATION_EDUCATION,
    RECOMMENDATION_INSTRUMENT_LIFECYCLE,
    RECOMMENDATION_OPERATIONAL_CAPACITY,
    RECOMMENDATION_QUALITY_TREND,
    InstrumentLifecycleForecast,
    OperationalForecast,
    PredictiveEducationSignal,
    PredictiveRecommendation,
    QualityTrendForecast,
)

_MIN_CONFIDENCE_TO_RECOMMEND = 0.3


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _already_open(db: Session, tenant_id: str, title: str) -> bool:
    return (
        db.query(PredictiveRecommendation.id)
        .filter(PredictiveRecommendation.tenant_id == tenant_id, PredictiveRecommendation.title == title, PredictiveRecommendation.status == "open")
        .first()
        is not None
    )


def _emit(db: Session, tenant_id: str, *, recommendation_type: str, title: str, evidence: list[dict], confidence_level: float, reasoning: str, suggested_action: str, source_type: str, source_id: int) -> PredictiveRecommendation | None:
    if _already_open(db, tenant_id, title):
        return None
    row = PredictiveRecommendation(
        tenant_id=tenant_id, recommendation_type=recommendation_type, title=title, evidence_json=json.dumps(evidence),
        confidence_level=confidence_level, reasoning=reasoning, suggested_action=suggested_action,
        source_type=source_type, source_id=source_id,
    )
    db.add(row)
    return row


def _latest_per_metric(db: Session, tenant_id: str) -> list[QualityTrendForecast]:
    rows = db.query(QualityTrendForecast).filter(QualityTrendForecast.tenant_id == tenant_id).order_by(QualityTrendForecast.id.desc()).all()
    seen = set()
    latest = []
    for r in rows:
        key = (r.metric, r.horizon)
        if key in seen:
            continue
        seen.add(key)
        latest.append(r)
    return latest


def generate_recommendations(db: Session, tenant_id: str) -> list[dict]:
    created: list[PredictiveRecommendation] = []

    for forecast in _latest_per_metric(db, tenant_id):
        adverse = (forecast.metric in ADVERSE_WHEN_INCREASING and forecast.trend_direction == "increasing") or \
                  (forecast.metric in ADVERSE_WHEN_DECREASING and forecast.trend_direction == "decreasing")
        if not adverse or forecast.confidence_level < _MIN_CONFIDENCE_TO_RECOMMEND:
            continue
        title = f"{forecast.metric.replace('_', ' ').title()} is trending {forecast.trend_direction} over the {forecast.horizon.replace('_', ' ')} horizon"
        direction_word = "decline" if forecast.metric in ADVERSE_WHEN_DECREASING else "increase"
        row = _emit(
            db, tenant_id, recommendation_type=RECOMMENDATION_QUALITY_TREND, title=title,
            evidence=json.loads(forecast.contributing_factors_json), confidence_level=forecast.confidence_level,
            reasoning=f"Forecast projects a {direction_word} in {forecast.metric.replace('_', ' ')} over the next {forecast.horizon.replace('_', ' ')}, based on {json.loads(forecast.historical_comparison_json).get('recent_14d_avg')} recent vs. prior activity.",
            suggested_action=f"Review {forecast.metric.replace('_', ' ')} practices and consider refresher education or maintenance review.",
            source_type="quality_trend_forecast", source_id=forecast.id,
        )
        if row is not None:
            created.append(row)

    lifecycle_rows = db.query(InstrumentLifecycleForecast).filter(InstrumentLifecycleForecast.tenant_id == tenant_id).order_by(InstrumentLifecycleForecast.id.desc()).all()
    seen_types = set()
    for f in lifecycle_rows:
        if f.instrument_type in seen_types:
            continue
        seen_types.add(f.instrument_type)
        if f.lifecycle_risk_tier not in ("high", "critical"):
            continue
        title = f"{f.instrument_type} instruments show {f.lifecycle_risk_tier} lifecycle risk"
        row = _emit(
            db, tenant_id, recommendation_type=RECOMMENDATION_INSTRUMENT_LIFECYCLE, title=title,
            evidence=json.loads(f.evidence_json), confidence_level=f.confidence_level,
            reasoning=f"Retirement likelihood is {f.retirement_likelihood}, driven by a corrosion progression score of {f.corrosion_progression_score} and recurring damage score of {f.recurring_damage_score}.",
            suggested_action=f"Schedule a lifecycle review for {f.instrument_type} instruments; consider planning for repair or replacement.",
            source_type="instrument_lifecycle_forecast", source_id=f.id,
        )
        if row is not None:
            created.append(row)

    op_rows = db.query(OperationalForecast).filter(OperationalForecast.tenant_id == tenant_id).order_by(OperationalForecast.id.desc()).all()
    seen_op = set()
    for o in op_rows:
        key = (o.forecast_type, o.horizon)
        if key in seen_op:
            continue
        seen_op.add(key)
        comparison = json.loads(o.forecast_detail_json) if o.forecast_detail_json else {}
        if o.forecast_value is None or o.confidence_level < _MIN_CONFIDENCE_TO_RECOMMEND:
            continue
        title = f"{o.forecast_type.replace('_', ' ').title()} projected at {round(o.forecast_value, 1)} over the {o.horizon.replace('_', ' ')} horizon"
        if _already_open(db, tenant_id, title):
            continue
        row = _emit(
            db, tenant_id, recommendation_type=RECOMMENDATION_OPERATIONAL_CAPACITY, title=title,
            evidence=[{"factor": "forecast_detail", "value": comparison}], confidence_level=o.confidence_level,
            reasoning=f"{o.forecast_type.replace('_', ' ').title()} is projected to reach {round(o.forecast_value, 1)} over the next {o.horizon.replace('_', ' ')}.",
            suggested_action="Review staffing and capacity plans against this projection.",
            source_type="operational_forecast", source_id=o.id,
        )
        if row is not None:
            created.append(row)

    education_rows = db.query(PredictiveEducationSignal).filter(PredictiveEducationSignal.tenant_id == tenant_id).order_by(PredictiveEducationSignal.id.desc()).limit(50).all()
    for e in education_rows:
        title = f"{e.scope_value}: {e.signal_type.replace('_', ' ')}"
        row = _emit(
            db, tenant_id, recommendation_type=RECOMMENDATION_EDUCATION, title=title,
            evidence=json.loads(e.evidence_json), confidence_level=e.confidence_level,
            reasoning=e.recommendation_text, suggested_action=e.recommendation_text,
            source_type="predictive_education_signal", source_id=e.id,
        )
        if row is not None:
            created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)

    return list_recommendations(db, tenant_id)


def list_recommendations(db: Session, tenant_id: str, *, status: str = "", recommendation_type: str = "") -> list[dict]:
    q = db.query(PredictiveRecommendation).filter(PredictiveRecommendation.tenant_id == tenant_id)
    if status:
        q = q.filter(PredictiveRecommendation.status == status)
    if recommendation_type:
        q = q.filter(PredictiveRecommendation.recommendation_type == recommendation_type)
    rows = q.order_by(PredictiveRecommendation.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def action_recommendation(db: Session, tenant_id: str, recommendation_id: int, *, actioned_by: str) -> dict | None:
    row = db.query(PredictiveRecommendation).filter(PredictiveRecommendation.id == recommendation_id, PredictiveRecommendation.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.status = "actioned"
    row.actioned_by = actioned_by
    row.actioned_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def dismiss_recommendation(db: Session, tenant_id: str, recommendation_id: int, *, actioned_by: str) -> dict | None:
    row = db.query(PredictiveRecommendation).filter(PredictiveRecommendation.id == recommendation_id, PredictiveRecommendation.tenant_id == tenant_id).first()
    if row is None:
        return None
    row.status = "dismissed"
    row.actioned_by = actioned_by
    row.actioned_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
