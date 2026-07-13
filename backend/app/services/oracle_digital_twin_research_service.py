"""Project Oracle, Section 5: Digital Twin Research.

Composes Apollo's governance-health digital-twin trajectory
(`apollo_quality_twin_service.twin_history`) and Vulcan's per-instrument
failure-progression model (`vulcan_progression_service.compute_progression`)
as data sources -- `underlying_snapshot_json` stores each function's own
already-computed output, never a re-derivation of either.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.oracle_discovery import CONFIDENCE_EXPLORATORY, OracleDigitalTwinInsight
from app.services import apollo_quality_twin_service, oracle_hypothesis_service, vulcan_progression_service
from app.models.vulcan_reliability import PROGRESSION_INSUFFICIENT_HISTORY


def to_dict(row: OracleDigitalTwinInsight) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "tenant_id": row.tenant_id,
        "facility_id": row.facility_id,
        "source_service": row.source_service,
        "source_reference": row.source_reference,
        "insight_summary": row.insight_summary,
        "underlying_snapshot": json.loads(row.underlying_snapshot_json or "{}"),
        "confidence_level": row.confidence_level,
        "promoted_to_hypothesis_id": row.promoted_to_hypothesis_id,
    }


def _summarize_apollo(history: list[dict]) -> str:
    if not history:
        return "No governance-health twin snapshots recorded yet for this department."
    latest = history[0]
    return (
        f"Latest governance-health twin snapshot (overall_score={latest.get('overall_score')}, "
        f"recorded {latest.get('created_at')}) against {len(history)} prior snapshot(s). Potential "
        f"association only; quality review recommended."
    )


def record_apollo_insight(
    db: Session, tenant_id: str, *, department: str = "unspecified", facility_id: str = "",
) -> OracleDigitalTwinInsight:
    history = apollo_quality_twin_service.twin_history(db, tenant_id, department=department, limit=20)
    row = OracleDigitalTwinInsight(
        tenant_id=tenant_id, facility_id=facility_id, source_service="apollo_quality_twin",
        source_reference=department, insight_summary=_summarize_apollo(history),
        underlying_snapshot_json=json.dumps({"department": department, "history": history[:5]}),
        confidence_level=CONFIDENCE_EXPLORATORY,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _summarize_vulcan(progression: dict, instrument_identity: str) -> str:
    if progression.get("progression") == PROGRESSION_INSUFFICIENT_HISTORY:
        return (
            f"Insufficient finding history for {instrument_identity} to characterize a progression trend "
            f"(recurrence_count={progression.get('recurrence_count', 0)})."
        )
    return (
        f"{instrument_identity} shows a '{progression.get('progression')}' finding-severity progression "
        f"(recurrence_count={progression.get('recurrence_count')}, confidence={progression.get('confidence')}) "
        f"over {progression.get('days_span')} days. Potential association only; quality review recommended."
    )


def record_vulcan_insight(
    db: Session, tenant_id: str, instrument_identity: str, *, zone: str | None = None, facility_id: str = "",
) -> OracleDigitalTwinInsight:
    progression = vulcan_progression_service.compute_progression(db, tenant_id, instrument_identity, zone=zone)
    source_reference = instrument_identity if not zone else f"{instrument_identity}:{zone}"
    row = OracleDigitalTwinInsight(
        tenant_id=tenant_id, facility_id=facility_id, source_service="vulcan_progression",
        source_reference=source_reference, insight_summary=_summarize_vulcan(progression, instrument_identity),
        underlying_snapshot_json=json.dumps(progression),
        confidence_level=progression.get("confidence", CONFIDENCE_EXPLORATORY),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_insights(db: Session, tenant_id: str, *, source_service: str = "") -> list[dict]:
    q = db.query(OracleDigitalTwinInsight).filter(OracleDigitalTwinInsight.tenant_id == tenant_id)
    if source_service:
        q = q.filter(OracleDigitalTwinInsight.source_service == source_service)
    return [to_dict(r) for r in q.order_by(OracleDigitalTwinInsight.created_at.desc()).all()]


def promote_to_hypothesis(
    db: Session, tenant_id: str, insight_id: int, *, discovery_category: str, title: str,
    hypothesis_statement: str = "", research_owner: str = "", changed_by: str = "", changed_by_role: str = "",
):
    insight = db.query(OracleDigitalTwinInsight).filter(
        OracleDigitalTwinInsight.tenant_id == tenant_id, OracleDigitalTwinInsight.id == insight_id,
    ).first()
    if insight is None:
        raise ValueError("Digital twin insight not found")
    if insight.promoted_to_hypothesis_id:
        raise ValueError("This digital twin insight has already been promoted to a hypothesis.")

    hyp = oracle_hypothesis_service.create_hypothesis(
        db, tenant_id, discovery_category=discovery_category, title=title, facility_id=insight.facility_id,
        research_owner=research_owner, observation_summary=insight.insight_summary,
        hypothesis_statement=hypothesis_statement or insight.insight_summary,
        related_instruments=[insight.source_reference] if insight.source_service == "vulcan_progression" else None,
        statistical_summary=json.loads(insight.underlying_snapshot_json or "{}"),
        changed_by=changed_by, changed_by_role=changed_by_role,
    )
    insight.promoted_to_hypothesis_id = hyp.id
    db.commit()
    oracle_hypothesis_service.link_digital_twin_ref(db, tenant_id, hyp.id, twin_insight_id=insight.id)
    return hyp
