"""v3.3 — Project Insight, Section 4: Predictive Education Engine.

Reuses `competency_intelligence_service.py` (Quality Guardian v2.9)
directly for supervisor-correction and image-quality-issue patterns —
those are not re-derived here. This module adds the two signal types
that codebase genuinely doesn't compute yet: a missed-anatomy-zone trend
and a coverage-decline trend, both per technician, both grounded in real
`Inspection` rows (`inspected_zones_json`, `coverage_pct`) via
`inspection_coverage.compute_coverage` — never fabricated, and silently
skipped (not flagged with a fake trend) for a technician with too few
assessed inspections in either comparison window.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.predictive_insight import (
    DISCLAIMER,
    SCOPE_TECHNICIAN,
    SIGNAL_COVERAGE_DECLINE_TREND,
    SIGNAL_MISSED_ANATOMY_ZONE_TREND,
    TREND_DECREASING,
    TREND_INCREASING,
    PredictiveEducationSignal,
)
from app.services import competency_intelligence_service
from app.services.inspection_coverage import compute_coverage
from app.services.insight_forecast_math import as_naive_utc

_RECENT_WINDOW_DAYS = 30
_PRIOR_WINDOW_DAYS = 30
_MIN_SAMPLE_PER_WINDOW = 3


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _windows() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    recent_since = now - timedelta(days=_RECENT_WINDOW_DAYS)
    prior_since = recent_since - timedelta(days=_PRIOR_WINDOW_DAYS)
    return prior_since, recent_since


def _technicians(db: Session, tenant_id: str) -> list[str]:
    rows = db.query(Inspection.technician).filter(Inspection.tenant_id == tenant_id).distinct().all()
    return [r[0] for r in rows if r[0]]


def _upsert(db: Session, tenant_id: str, *, scope_value: str, signal_type: str, trend_direction: str, confidence_level: float, evidence: list[dict], recommendation_text: str) -> PredictiveEducationSignal:
    row = PredictiveEducationSignal(
        tenant_id=tenant_id, scope_type=SCOPE_TECHNICIAN, scope_value=scope_value, signal_type=signal_type,
        trend_direction=trend_direction, confidence_level=confidence_level,
        evidence_json=json.dumps(evidence), recommendation_text=recommendation_text,
    )
    db.add(row)
    return row


def _missed_anatomy_zone_signals(db: Session, tenant_id: str) -> list[PredictiveEducationSignal]:
    prior_since, recent_since = _windows()
    signals = []

    for technician in _technicians(db, tenant_id):
        rows = (
            db.query(Inspection)
            .filter(Inspection.tenant_id == tenant_id, Inspection.technician == technician, Inspection.created_at >= prior_since)
            .all()
        )
        recent_missing, prior_missing = [], []
        for r in rows:
            try:
                zones = json.loads(r.inspected_zones_json or "null")
            except (TypeError, ValueError):
                zones = None
            cov = compute_coverage(r.instrument_type, zones)
            if not cov["assessed"]:
                continue
            bucket = recent_missing if as_naive_utc(r.created_at) >= as_naive_utc(recent_since) else prior_missing
            bucket.append(len(cov["missing"]))

        if len(recent_missing) < _MIN_SAMPLE_PER_WINDOW or len(prior_missing) < _MIN_SAMPLE_PER_WINDOW:
            continue

        recent_avg = sum(recent_missing) / len(recent_missing)
        prior_avg = sum(prior_missing) / len(prior_missing)
        if recent_avg <= prior_avg + 0.5:
            continue  # not a meaningful increase — no signal, not a fabricated one

        confidence = round(min(0.9, 0.2 + min(len(recent_missing), len(prior_missing)) * 0.08), 3)
        evidence = [
            {"factor": "avg_missed_zones_recent_30d", "value": round(recent_avg, 2), "signal": "elevated"},
            {"factor": "avg_missed_zones_prior_30d", "value": round(prior_avg, 2), "signal": "baseline"},
            {"factor": "sample_size", "value": f"{len(recent_missing)} recent / {len(prior_missing)} prior", "signal": "sufficient"},
        ]
        signals.append(_upsert(
            db, tenant_id, scope_value=technician, signal_type=SIGNAL_MISSED_ANATOMY_ZONE_TREND, trend_direction=TREND_INCREASING,
            confidence_level=confidence, evidence=evidence,
            recommendation_text=f"{technician}'s average missed anatomy zones per inspection rose from {round(prior_avg, 1)} to {round(recent_avg, 1)} over the last 30 days. Consider a refresher on anatomy zone coverage.",
        ))

    return signals


def _coverage_decline_signals(db: Session, tenant_id: str) -> list[PredictiveEducationSignal]:
    prior_since, recent_since = _windows()
    signals = []

    for technician in _technicians(db, tenant_id):
        rows = (
            db.query(Inspection)
            .filter(
                Inspection.tenant_id == tenant_id, Inspection.technician == technician, Inspection.created_at >= prior_since,
                Inspection.coverage_pct.isnot(None),
            )
            .all()
        )
        recent = [r.coverage_pct for r in rows if as_naive_utc(r.created_at) >= as_naive_utc(recent_since)]
        prior = [r.coverage_pct for r in rows if as_naive_utc(r.created_at) < as_naive_utc(recent_since)]

        if len(recent) < _MIN_SAMPLE_PER_WINDOW or len(prior) < _MIN_SAMPLE_PER_WINDOW:
            continue

        recent_avg = sum(recent) / len(recent)
        prior_avg = sum(prior) / len(prior)
        if recent_avg >= prior_avg - 5:
            continue  # not a meaningful decline

        confidence = round(min(0.9, 0.2 + min(len(recent), len(prior)) * 0.08), 3)
        evidence = [
            {"factor": "avg_coverage_pct_recent_30d", "value": round(recent_avg, 1), "signal": "declining"},
            {"factor": "avg_coverage_pct_prior_30d", "value": round(prior_avg, 1), "signal": "baseline"},
            {"factor": "sample_size", "value": f"{len(recent)} recent / {len(prior)} prior", "signal": "sufficient"},
        ]
        signals.append(_upsert(
            db, tenant_id, scope_value=technician, signal_type=SIGNAL_COVERAGE_DECLINE_TREND, trend_direction=TREND_DECREASING,
            confidence_level=confidence, evidence=evidence,
            recommendation_text=f"{technician}'s average inspection coverage declined from {round(prior_avg, 1)}% to {round(recent_avg, 1)}% over the last 30 days. Consider a coverage refresher.",
        ))

    return signals


def generate_predictive_education_signals(db: Session, tenant_id: str) -> dict:
    new_signals = _missed_anatomy_zone_signals(db, tenant_id) + _coverage_decline_signals(db, tenant_id)
    db.commit()
    for s in new_signals:
        db.refresh(s)

    return {
        "new_signals": [_row_to_dict(s) for s in new_signals],
        "existing_competency_opportunities": competency_intelligence_service.detect_competency_opportunities(db, tenant_id),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def list_education_signals(db: Session, tenant_id: str, *, signal_type: str = "") -> list[dict]:
    q = db.query(PredictiveEducationSignal).filter(PredictiveEducationSignal.tenant_id == tenant_id)
    if signal_type:
        q = q.filter(PredictiveEducationSignal.signal_type == signal_type)
    rows = q.order_by(PredictiveEducationSignal.id.desc()).limit(50).all()
    return [_row_to_dict(r) for r in rows]
