"""Project Oracle, Section 4: Emerging Trend Detection.

Deliberately **tenant-scoped**, working directly off one tenant's own
`InspectionFinding` history with no network-enrollment precondition -- see
the naming disambiguation in `app/models/oracle_discovery.py` for why this
is independent of Horizon's network-wide `EmergingTrendAlert`
(`horizon_trend_detection_service.detect_emerging_trends`), which requires
peer-tenant enrollment and would return nothing for a single-tenant
deployment.

The trend calculation itself is a plain two-window comparison (a recent
window vs. the equal-length window before it) -- never a claim of
statistical significance, only a graded `statistical_confidence` of
low/moderate, and `direction` is always paired with the raw counts in
`data_points_json` so a reviewer can see exactly what produced it.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.inspection_finding import InspectionFinding
from app.models.oracle_discovery import DISCOVERY_CATEGORIES, OracleTrendObservation
from app.services import oracle_hypothesis_service


def to_dict(row: OracleTrendObservation) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "tenant_id": row.tenant_id,
        "facility_id": row.facility_id,
        "trend_category": row.trend_category,
        "metric_name": row.metric_name,
        "observation_window_start": row.observation_window_start.isoformat() if row.observation_window_start else None,
        "observation_window_end": row.observation_window_end.isoformat() if row.observation_window_end else None,
        "data_points": json.loads(row.data_points_json or "[]"),
        "direction": row.direction,
        "magnitude": row.magnitude,
        "statistical_confidence": row.statistical_confidence,
        "promoted_to_hypothesis_id": row.promoted_to_hypothesis_id,
        "notes": row.notes,
    }


def _finding_count(db: Session, tenant_id: str, department: str, start: datetime, end: datetime) -> int:
    q = (
        db.query(InspectionFinding)
        .join(models.Inspection, InspectionFinding.inspection_id == models.Inspection.id)
        .filter(
            models.Inspection.tenant_id == tenant_id,
            models.Inspection.created_at >= start,
            models.Inspection.created_at < end,
        )
    )
    if department:
        q = q.filter(models.Inspection.department == department)
    return q.count()


def detect_finding_rate_trend(
    db: Session, tenant_id: str, *, trend_category: str, metric_name: str, facility_id: str = "",
    department: str = "", window_days: int = 30,
) -> OracleTrendObservation:
    if trend_category not in DISCOVERY_CATEGORIES:
        raise ValueError(f"Unknown discovery category: {trend_category}")

    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(days=window_days)
    prior_start = window_start - timedelta(days=window_days)

    recent = _finding_count(db, tenant_id, department, window_start, window_end)
    prior = _finding_count(db, tenant_id, department, prior_start, window_start)

    if prior == 0 and recent == 0:
        direction, magnitude, confidence = "stable", 0.0, "low"
    elif prior == 0:
        direction, magnitude, confidence = "increasing", float(recent), "low"
    else:
        pct_change = (recent - prior) / prior
        magnitude = round(pct_change, 3)
        if pct_change > 0.15:
            direction = "increasing"
        elif pct_change < -0.15:
            direction = "decreasing"
        else:
            direction = "stable"
        confidence = "moderate" if abs(recent - prior) >= 5 else "low"

    row = OracleTrendObservation(
        tenant_id=tenant_id, facility_id=facility_id, trend_category=trend_category, metric_name=metric_name,
        observation_window_start=window_start, observation_window_end=window_end,
        data_points_json=json.dumps([
            {"window": "prior", "start": prior_start.isoformat(), "end": window_start.isoformat(), "count": prior},
            {"window": "recent", "start": window_start.isoformat(), "end": window_end.isoformat(), "count": recent},
        ]),
        direction=direction, magnitude=magnitude, statistical_confidence=confidence,
        notes=(
            f"{metric_name}: {prior} findings in the prior {window_days}-day window vs. {recent} in the most "
            f"recent {window_days}-day window. Potential association only; quality review recommended."
        ),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_trend_observations(
    db: Session, tenant_id: str, *, trend_category: str = "", direction: str = "",
) -> list[dict]:
    q = db.query(OracleTrendObservation).filter(OracleTrendObservation.tenant_id == tenant_id)
    if trend_category:
        q = q.filter(OracleTrendObservation.trend_category == trend_category)
    if direction:
        q = q.filter(OracleTrendObservation.direction == direction)
    return [to_dict(r) for r in q.order_by(OracleTrendObservation.created_at.desc()).all()]


def promote_to_hypothesis(
    db: Session, tenant_id: str, trend_observation_id: int, *, title: str, hypothesis_statement: str = "",
    research_owner: str = "", changed_by: str = "", changed_by_role: str = "",
):
    trend = db.query(OracleTrendObservation).filter(
        OracleTrendObservation.tenant_id == tenant_id, OracleTrendObservation.id == trend_observation_id,
    ).first()
    if trend is None:
        raise ValueError("Trend observation not found")
    if trend.promoted_to_hypothesis_id:
        raise ValueError("This trend observation has already been promoted to a hypothesis.")

    hyp = oracle_hypothesis_service.create_hypothesis(
        db, tenant_id, discovery_category=trend.trend_category, title=title, facility_id=trend.facility_id,
        research_owner=research_owner,
        observation_summary=trend.notes,
        hypothesis_statement=hypothesis_statement or (
            f"There may be a possible association between {trend.metric_name} and the observed "
            f"{trend.direction} trend; quality review recommended."
        ),
        statistical_summary={
            "trend_observation_id": trend.id, "direction": trend.direction, "magnitude": trend.magnitude,
            "statistical_confidence": trend.statistical_confidence,
        },
        changed_by=changed_by, changed_by_role=changed_by_role,
    )
    trend.promoted_to_hypothesis_id = hyp.id
    db.commit()
    return hyp
