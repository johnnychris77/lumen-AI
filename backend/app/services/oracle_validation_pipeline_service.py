"""Project Oracle, Section 10: the 8-stage validation pipeline
(Observation -> Hypothesis -> Evidence Review -> Scientific Validation ->
Pilot Study -> Clinical Review -> Governance Approval -> Production
Knowledge). Oracle may not bypass any stage:

  * `advance_stage` only ever moves a hypothesis to the single next entry
    in `VALIDATION_STAGES` -- there is no "skip ahead" parameter.
  * `close_out_hypothesis` moves a hypothesis straight to the terminal
    `REJECTED` stage from any non-terminal stage (a hypothesis can be
    rejected, withdrawn, or found inconclusive at any point -- it never
    needs to first climb the ladder to be closed).
  * Promoting to `PRODUCTION_KNOWLEDGE` -- the only stage that authorizes
    a discovery to influence real production behavior -- requires
    manager-tier-or-above authorization (`ROLE_AUTHORITY_TIER`), the same
    threshold Council and Steward use for their own high-authority gates.

Every transition is recorded in `OracleStageTransition`, an append-only
audit trail -- never mutated or deleted.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.oracle_discovery import (
    OUTCOME_INCONCLUSIVE,
    OUTCOME_PROMOTED,
    OUTCOME_REJECTED,
    OUTCOME_WITHDRAWN,
    ROLE_AUTHORITY_TIER,
    STAGE_PRODUCTION_KNOWLEDGE,
    STAGE_REJECTED,
    TERMINAL_STAGES,
    TIER_PROMOTE_TO_PRODUCTION_KNOWLEDGE,
    VALIDATION_STAGES,
    OracleHypothesis,
    OracleStageTransition,
)
from app.services import oracle_hypothesis_service

_CLOSURE_OUTCOMES = {OUTCOME_REJECTED, OUTCOME_WITHDRAWN, OUTCOME_INCONCLUSIVE}


def _transition_to_dict(row: OracleStageTransition) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "hypothesis_id": row.hypothesis_id,
        "from_stage": row.from_stage,
        "to_stage": row.to_stage,
        "changed_by": row.changed_by,
        "changed_by_role": row.changed_by_role,
        "gate_check_notes": row.gate_check_notes,
        "reason": row.reason,
    }


def stage_history(db: Session, tenant_id: str, hypothesis_id: int) -> list[dict]:
    rows = (
        db.query(OracleStageTransition)
        .filter(OracleStageTransition.tenant_id == tenant_id, OracleStageTransition.hypothesis_id == hypothesis_id)
        .order_by(OracleStageTransition.created_at.asc())
        .all()
    )
    return [_transition_to_dict(r) for r in rows]


def advance_stage(
    db: Session, tenant_id: str, hypothesis_id: int, *, changed_by: str, changed_by_role: str,
    gate_check_notes: str = "", reason: str = "",
) -> OracleHypothesis:
    hyp = oracle_hypothesis_service.get_hypothesis(db, tenant_id, hypothesis_id)
    if hyp is None:
        raise ValueError("Hypothesis not found")
    if hyp.current_stage in TERMINAL_STAGES:
        raise ValueError(f"Hypothesis is already {hyp.current_stage} and cannot advance further.")

    idx = VALIDATION_STAGES.index(hyp.current_stage)
    if idx == len(VALIDATION_STAGES) - 1:
        raise ValueError("Hypothesis is already at the final validation stage.")
    next_stage = VALIDATION_STAGES[idx + 1]

    if next_stage == STAGE_PRODUCTION_KNOWLEDGE:
        actor_tier = ROLE_AUTHORITY_TIER.get(changed_by_role, 0)
        if actor_tier < TIER_PROMOTE_TO_PRODUCTION_KNOWLEDGE:
            raise ValueError(
                f"Role '{changed_by_role}' (tier {actor_tier}) is not authorized to promote a hypothesis to "
                f"PRODUCTION_KNOWLEDGE; requires tier {TIER_PROMOTE_TO_PRODUCTION_KNOWLEDGE} or higher."
            )
        if not gate_check_notes.strip():
            raise ValueError("Promoting to PRODUCTION_KNOWLEDGE requires gate-check notes recording what was reviewed.")

    from_stage = hyp.current_stage
    hyp.current_stage = next_stage
    if next_stage == STAGE_PRODUCTION_KNOWLEDGE:
        hyp.outcome = OUTCOME_PROMOTED
    hyp.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(hyp)
    db.add(OracleStageTransition(
        tenant_id=tenant_id, hypothesis_id=hyp.id, from_stage=from_stage, to_stage=next_stage,
        changed_by=changed_by, changed_by_role=changed_by_role, gate_check_notes=gate_check_notes, reason=reason,
    ))
    db.commit()
    return hyp


def close_out_hypothesis(
    db: Session, tenant_id: str, hypothesis_id: int, *, outcome: str, changed_by: str, changed_by_role: str,
    reason: str,
) -> OracleHypothesis:
    if outcome not in _CLOSURE_OUTCOMES:
        raise ValueError(f"Closure outcome must be one of {sorted(_CLOSURE_OUTCOMES)}, got '{outcome}'.")
    if not reason.strip():
        raise ValueError("Closing out a hypothesis requires a reason.")
    hyp = oracle_hypothesis_service.get_hypothesis(db, tenant_id, hypothesis_id)
    if hyp is None:
        raise ValueError("Hypothesis not found")
    if hyp.current_stage in TERMINAL_STAGES:
        raise ValueError(f"Hypothesis is already {hyp.current_stage} and cannot be closed out again.")

    from_stage = hyp.current_stage
    hyp.current_stage = STAGE_REJECTED
    hyp.outcome = outcome
    hyp.rejected_reason = reason
    hyp.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(hyp)
    db.add(OracleStageTransition(
        tenant_id=tenant_id, hypothesis_id=hyp.id, from_stage=from_stage, to_stage=STAGE_REJECTED,
        changed_by=changed_by, changed_by_role=changed_by_role, reason=reason,
    ))
    db.commit()
    return hyp
