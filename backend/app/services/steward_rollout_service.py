"""Project Steward, Section 8: Pilot and Rollout Management.

Tracked as `GovernedActionRollout` rows -- see `governed_action.py`'s
naming disambiguation for why nothing here is named `pilot_*` despite the
brief's own vocabulary ("single-instrument pilot", "facility pilot",
etc.), which is preserved only as `rollout_scope` data values.

No rollout automatically advances to a broader scope -- `record_go_no_go`
only ever records the decision; a caller must separately create the next,
broader-scope rollout row.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.governed_action import GovernedActionRollout, ROLLOUT_SCOPES
from app.services import steward_action_service


def to_dict(row: GovernedActionRollout) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "governed_action_id": row.governed_action_id,
        "rollout_scope": row.rollout_scope,
        "scope_value": row.scope_value,
        "start_date": row.start_date.isoformat() if row.start_date else None,
        "baseline_metrics": json.loads(row.baseline_metrics_json or "{}"),
        "expected_result": row.expected_result,
        "actual_result": row.actual_result,
        "adverse_effects": row.adverse_effects,
        "user_feedback": row.user_feedback,
        "go_no_go_decision": row.go_no_go_decision,
        "rolled_back": row.rolled_back,
    }


def create_rollout(
    db: Session, tenant_id: str, action_id: int, *, rollout_scope: str, scope_value: str = "",
    start_date: datetime | None = None, baseline_metrics: dict | None = None, expected_result: str = "",
) -> GovernedActionRollout:
    if rollout_scope not in ROLLOUT_SCOPES:
        raise ValueError(f"Unknown rollout scope: {rollout_scope}")
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise ValueError("Governed Action not found")
    row = GovernedActionRollout(
        tenant_id=tenant_id, governed_action_id=action_id, rollout_scope=rollout_scope, scope_value=scope_value,
        start_date=start_date or datetime.now(timezone.utc), baseline_metrics_json=json.dumps(baseline_metrics or {}),
        expected_result=expected_result,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_rollouts(db: Session, tenant_id: str, action_id: int) -> list[dict]:
    rows = (
        db.query(GovernedActionRollout)
        .filter(GovernedActionRollout.tenant_id == tenant_id, GovernedActionRollout.governed_action_id == action_id)
        .order_by(GovernedActionRollout.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]


def record_rollout_result(
    db: Session, tenant_id: str, rollout_id: int, *, actual_result: str = "", adverse_effects: str = "",
    user_feedback: str = "",
) -> GovernedActionRollout:
    row = db.query(GovernedActionRollout).filter(
        GovernedActionRollout.tenant_id == tenant_id, GovernedActionRollout.id == rollout_id,
    ).first()
    if row is None:
        raise ValueError("Rollout not found")
    row.actual_result = actual_result
    row.adverse_effects = adverse_effects
    row.user_feedback = user_feedback
    db.commit()
    db.refresh(row)
    return row


def record_go_no_go(db: Session, tenant_id: str, rollout_id: int, *, decision: str, rolled_back: bool = False) -> GovernedActionRollout:
    """Section 8: no rollout automatically advances to broader rollout --
    this only records the decision on this rollout row."""
    if decision not in ("go", "no_go"):
        raise ValueError("go_no_go decision must be 'go' or 'no_go'")
    row = db.query(GovernedActionRollout).filter(
        GovernedActionRollout.tenant_id == tenant_id, GovernedActionRollout.id == rollout_id,
    ).first()
    if row is None:
        raise ValueError("Rollout not found")
    row.go_no_go_decision = decision
    row.rolled_back = rolled_back
    db.commit()
    db.refresh(row)
    return row
