"""Project Steward, Section 25: Decision-to-Outcome Timeline.

Stitches together every real, already-persisted record for one Governed
Action into a single chronological timeline -- nothing here is
fabricated; each event is either the action's own approval fields or a
row from one of Steward's child tables.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import (
    steward_action_service,
    steward_benefits_realization_service,
    steward_residual_risk_service,
    steward_rollout_service,
    steward_unintended_consequence_service,
    steward_verification_service,
)


def decision_to_outcome_timeline(db: Session, tenant_id: str, action_id: int) -> dict:
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    data = steward_action_service.to_dict(action)

    events: list[dict] = [{
        "stage": "specialist_analysis_and_human_approval", "timestamp": data["approval_timestamp"],
        "detail": f"Approved by {data['approved_by']}: {data['source_decision']}",
    }]
    for e in steward_action_service.audit_history(db, tenant_id, action_id):
        events.append({"stage": "implementation", "timestamp": e["created_at"], "detail": f"{e['from_status'] or '(new)'} -> {e['to_status']}: {e['reason']}"})
    for v in steward_verification_service.list_verifications(db, tenant_id, action_id):
        events.append({"stage": "verification", "timestamp": v["verified_at"] or v["created_at"], "detail": f"{v['evidence_type']}: sufficient={v['sufficient']}"})
    for r in steward_rollout_service.list_rollouts(db, tenant_id, action_id):
        events.append({"stage": "implementation", "timestamp": r["created_at"], "detail": f"Rollout ({r['rollout_scope']}): {r['go_no_go_decision'] or 'pending'}"})
    for o in steward_benefits_realization_service.list_outcome_reviews(db, tenant_id, action_id):
        events.append({"stage": "outcome_measurement_and_benefits_realization", "timestamp": o["created_at"], "detail": f"{o['metric_name']}: {o['classification']}"})
    for c in steward_unintended_consequence_service.list_consequences(db, tenant_id, action_id):
        events.append({"stage": "outcome_measurement_and_benefits_realization", "timestamp": c["created_at"], "detail": f"Unintended consequence: {c['consequence_type']}"})
    for rr in steward_residual_risk_service.list_residual_risk_reviews(db, tenant_id, action_id):
        events.append({"stage": "outcome_measurement_and_benefits_realization", "timestamp": rr["created_at"], "detail": f"Residual risk before={rr['risk_before']} after={rr['risk_after']}"})
    if data["closure_decision"]:
        events.append({"stage": "closure", "timestamp": data["closed_at"], "detail": f"{data['closure_decision']} (approved by {data['closure_approver']})"})

    events = [e for e in events if e["timestamp"]]
    events.sort(key=lambda e: e["timestamp"])
    return {"governed_action_id": action_id, "events": events, "human_review_required": True}
