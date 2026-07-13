"""Project Oracle, Section 7: AI Model Observatory.

Composes Sentinel-X's own `sentinel_ai_health_service.compute_ai_health`
return dict verbatim -- Oracle never recomputes drift detection, confidence
calibration, or supervisor-agreement metrics; it only observes and frames
Sentinel-X's own already-computed judgment for research purposes.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.oracle_discovery import OracleModelObservation
from app.services import oracle_hypothesis_service, sentinel_ai_health_service

_OBS_DRIFT = "drift_detected"
_OBS_CALIBRATION_SHIFT = "confidence_calibration_shift"
_OBS_COVERAGE_GAP = "coverage_gap"
_OBS_ROUTINE_SNAPSHOT = "routine_snapshot"


def to_dict(row: OracleModelObservation) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "tenant_id": row.tenant_id,
        "model_scope": row.model_scope,
        "observation_type": row.observation_type,
        "ai_health_snapshot": json.loads(row.ai_health_snapshot_json or "{}"),
        "summary": row.summary,
        "reviewed": row.reviewed,
        "reviewed_by": row.reviewed_by,
        "promoted_to_hypothesis_id": row.promoted_to_hypothesis_id,
    }


def record_observation(db: Session, tenant_id: str, *, model_scope: str = "supervisor_ai") -> OracleModelObservation:
    health = sentinel_ai_health_service.compute_ai_health(db, tenant_id)

    if health.get("drift_detected"):
        observation_type = _OBS_DRIFT
        summary = f"Drift detected: {health.get('drift_detail')}. Potential association only; quality review recommended."
    elif health.get("coverage_quality_pct") is not None and health["coverage_quality_pct"] < 50:
        observation_type = _OBS_COVERAGE_GAP
        summary = (
            f"Coverage quality is low ({health['coverage_quality_pct']}%), which may limit how reliable this "
            f"model-health snapshot is. Quality review recommended."
        )
    else:
        observation_type = _OBS_ROUTINE_SNAPSHOT
        summary = "Routine AI model-health snapshot; no drift or coverage gap detected."

    row = OracleModelObservation(
        tenant_id=tenant_id, model_scope=model_scope, observation_type=observation_type,
        ai_health_snapshot_json=json.dumps(health), summary=summary,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_observations(db: Session, tenant_id: str, *, observation_type: str = "", reviewed: bool | None = None) -> list[dict]:
    q = db.query(OracleModelObservation).filter(OracleModelObservation.tenant_id == tenant_id)
    if observation_type:
        q = q.filter(OracleModelObservation.observation_type == observation_type)
    if reviewed is not None:
        q = q.filter(OracleModelObservation.reviewed == reviewed)
    return [to_dict(r) for r in q.order_by(OracleModelObservation.created_at.desc()).all()]


def mark_reviewed(db: Session, tenant_id: str, observation_id: int, *, reviewed_by: str) -> OracleModelObservation:
    row = db.query(OracleModelObservation).filter(
        OracleModelObservation.tenant_id == tenant_id, OracleModelObservation.id == observation_id,
    ).first()
    if row is None:
        raise ValueError("Model observation not found")
    row.reviewed = True
    row.reviewed_by = reviewed_by
    db.commit()
    db.refresh(row)
    return row


def promote_to_hypothesis(
    db: Session, tenant_id: str, observation_id: int, *, title: str, hypothesis_statement: str = "",
    research_owner: str = "", changed_by: str = "", changed_by_role: str = "",
):
    obs = db.query(OracleModelObservation).filter(
        OracleModelObservation.tenant_id == tenant_id, OracleModelObservation.id == observation_id,
    ).first()
    if obs is None:
        raise ValueError("Model observation not found")
    if obs.promoted_to_hypothesis_id:
        raise ValueError("This model observation has already been promoted to a hypothesis.")

    hyp = oracle_hypothesis_service.create_hypothesis(
        db, tenant_id, discovery_category="ai_model_performance_drift", title=title, research_owner=research_owner,
        observation_summary=obs.summary, hypothesis_statement=hypothesis_statement or obs.summary,
        statistical_summary=json.loads(obs.ai_health_snapshot_json or "{}"),
        changed_by=changed_by, changed_by_role=changed_by_role,
    )
    obs.promoted_to_hypothesis_id = hyp.id
    db.commit()
    return hyp
