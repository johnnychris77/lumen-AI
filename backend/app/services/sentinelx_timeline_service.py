"""Project Sentinel-X, Section 7: Risk Timeline.

A chronological, real-data timeline for one instrument -- findings,
supervisor reviews, and repairs (each with a real timestamp), followed by
the current Digital Twin condition trend and the most recent risk
assessment. Never a fabricated "Education" stage when no instrument-
specific education record exists -- omitted rather than invented.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sentinelx_risk import SentinelXRiskAssessment
from app.models.supervisor_review import SupervisorReview
from app.services.instrument_condition_service import instrument_condition_history
from app.services.vulcan_progression_service import _inspections_for_identity, findings_timeline
from app.services.vulcan_repair_effectiveness_service import repair_history_for_instrument


def build_risk_timeline(db: Session, tenant_id: str, instrument_identity: str) -> dict:
    events: list[dict] = []

    for row in findings_timeline(db, tenant_id, instrument_identity):
        events.append({
            "stage": "finding", "at": row["created_at"].isoformat() if row["created_at"] else None,
            "detail": f"{row['finding_type']} at {row['zone']} (severity {row['severity_index']})",
        })

    inspections = _inspections_for_identity(db, tenant_id, instrument_identity)
    insp_ids = [i.id for i in inspections]
    if insp_ids:
        reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id, SupervisorReview.inspection_id.in_(insp_ids)).all()
        for r in reviews:
            events.append({
                "stage": "supervisor", "at": r.created_at.isoformat() if r.created_at else None,
                "detail": f"Supervisor {r.agreement} (finding_correct={r.finding_correct}, zone_correct={r.zone_correct})",
            })

    for repair in repair_history_for_instrument(db, tenant_id, instrument_identity):
        events.append({
            "stage": "repair", "at": None,
            "detail": f"Repair outcome: {repair['repair_outcome']} (vendor: {repair['evidence'].get('vendor_name', '')})",
        })

    events = [e for e in events if e["at"] is not None]
    events.sort(key=lambda e: e["at"])

    condition = instrument_condition_history(db, tenant_id, instrument_identity)
    current_twin_trend = condition["condition_trend"] if condition else "insufficient_data"

    latest_risk = (
        db.query(SentinelXRiskAssessment)
        .filter(SentinelXRiskAssessment.tenant_id == tenant_id, SentinelXRiskAssessment.instrument_identity == instrument_identity)
        .order_by(SentinelXRiskAssessment.created_at.desc())
        .first()
    )

    return {
        "instrument_identity": instrument_identity,
        "events": events,
        "current_digital_twin_trend": current_twin_trend,
        "current_risk": {
            "risk_score": latest_risk.risk_score, "risk_level": latest_risk.risk_level,
            "assessed_at": latest_risk.created_at.isoformat() if latest_risk.created_at else None,
        } if latest_risk else None,
    }
