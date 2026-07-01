"""Phase 14.8 — Predictive Instrument Intelligence.

Builds a per-instrument inspection timeline and an honest, deterministic
prediction (risk trend + estimated remaining useful life) from the instrument's
own inspection history. No fabricated ML — trends are computed from recorded
risk scores; projections are clearly labeled estimates.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db import models

# Risk score (0-100, higher = worse) at/after which an instrument is flagged.
_RETIRE_RISK = 70


def _entry(row: models.Inspection) -> dict[str, Any]:
    score = (100 - row.risk_score) if row.score_status == "scored" else None
    return {
        "inspection_id": row.id,
        "date": row.created_at.isoformat() if row.created_at else None,
        "inspection_score": score,
        "risk_score": row.risk_score,
        "risk_level": row.risk_level,
        "cleaning": row.overall_cleaning_assessment,
        "recommended_action": row.recommended_action,
        "supervisor_review_required": row.supervisor_review_required,
    }


def _trend(risk_scores: list[int]) -> str:
    """improving / stable / worsening from the risk-score series (higher=worse)."""
    if len(risk_scores) < 2:
        return "insufficient_data"
    half = len(risk_scores) // 2 or 1
    early = sum(risk_scores[:half]) / half
    late = sum(risk_scores[half:]) / (len(risk_scores) - half)
    delta = late - early
    if delta > 8:
        return "worsening"
    if delta < -8:
        return "improving"
    return "stable"


def instrument_timeline(db: Session, identifier: str, tenant_id: str) -> dict[str, Any]:
    """Return the inspection timeline + prediction for an instrument identifier
    (barcode or UDI)."""
    rows = (
        db.query(models.Inspection)
        .filter(
            models.Inspection.tenant_id == tenant_id,
            or_(
                models.Inspection.instrument_barcode == identifier,
                models.Inspection.instrument_udi == identifier,
            ),
        )
        .order_by(models.Inspection.created_at.asc(), models.Inspection.id.asc())
        .all()
    )

    timeline = [_entry(r) for r in rows]
    risk_scores = [r.risk_score for r in rows if r.score_status == "scored"]
    trend = _trend(risk_scores)

    # Honest remaining-useful-life estimate: project the risk slope forward to the
    # retirement threshold. Only offered when there is a clear worsening trend.
    remaining_estimate: str | None = None
    if trend == "worsening" and len(risk_scores) >= 2:
        slope = (risk_scores[-1] - risk_scores[0]) / max(1, len(risk_scores) - 1)
        if slope > 0 and risk_scores[-1] < _RETIRE_RISK:
            inspections_left = int((_RETIRE_RISK - risk_scores[-1]) / slope)
            remaining_estimate = (
                f"~{max(1, inspections_left)} more inspections before the risk "
                f"threshold, at the current rate (estimate)."
            )
        elif risk_scores[-1] >= _RETIRE_RISK:
            remaining_estimate = "Already at/above the risk threshold — plan replacement."

    latest = rows[-1] if rows else None
    prediction = {
        "risk_trend": trend,
        "latest_risk_score": risk_scores[-1] if risk_scores else None,
        "estimated_remaining_life": remaining_estimate,
        "replacement_planning": (
            "Plan replacement/repair evaluation."
            if (latest and latest.supervisor_review_required)
            or (risk_scores and risk_scores[-1] >= _RETIRE_RISK)
            else "No replacement action indicated at this time."
        ),
        "note": (
            "Trend and estimate are derived from recorded inspection risk scores — "
            "a deterministic projection, not a validated predictive model."
        ),
    }

    return {
        "identifier": identifier,
        "inspection_count": len(timeline),
        "timeline": timeline,
        "prediction": prediction,
    }
