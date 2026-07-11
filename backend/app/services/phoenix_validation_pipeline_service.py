"""v4.9 — Project Phoenix, Section 9: Continuous Validation.

Every recommendation moves through Review -> Clinical Validation ->
Technical Review -> Pilot -> Measurement -> Production. Rather than a
second approval-chain model, this reuses Project Forge's existing
`WorkflowApprovalChain`/`WorkflowApprovalInstance` primitive
(`forge_approval_service.py`, v4.1) directly — one chain per
recommendation, with the six Phoenix stages as its ordered steps.
A rejection at any stage ends the instance immediately (Forge's existing
behavior) and the recommendation's `status` is set to `rejected` — no
recommendation ever reaches `production` without an explicit approval at
every stage.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.phoenix_intelligence import DISCLAIMER, STAGE_REVIEW, VALIDATION_STAGES, ImprovementRecommendation, ValidationOutcome
from app.services import forge_approval_service


class RecommendationNotFoundError(ValueError):
    pass


def _get_recommendation(db: Session, tenant_id: str, recommendation_id: int) -> ImprovementRecommendation:
    row = (
        db.query(ImprovementRecommendation)
        .filter(ImprovementRecommendation.id == recommendation_id, ImprovementRecommendation.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise RecommendationNotFoundError(f"Recommendation {recommendation_id} not found for tenant {tenant_id}.")
    return row


def start_validation(db: Session, tenant_id: str, recommendation_id: int) -> dict:
    """Creates the six-stage approval chain for a recommendation and
    starts its instance at stage 0 (Review)."""
    rec = _get_recommendation(db, tenant_id, recommendation_id)
    chain = forge_approval_service.create_chain(db, tenant_id, name=f"Validation: {rec.title}", steps=VALIDATION_STAGES)
    instance = forge_approval_service.start_instance(db, tenant_id, chain["id"])

    rec.approval_chain_id = chain["id"]
    rec.approval_instance_id = instance["id"]
    rec.status = STAGE_REVIEW
    db.commit()
    db.refresh(rec)
    return {"recommendation_id": rec.id, "chain": chain, "instance": instance}


def advance_validation(
    db: Session, tenant_id: str, recommendation_id: int, *, decided_by: str, decided_role: str, decision: str,
    notes: str = "", outcome_notes: str = "", lessons_learned: str = "", measured_impact: str = "",
) -> dict:
    """Records one stage's decision. On approval, advances to the next
    stage (or `production` if this was the final stage); on rejection,
    ends the pipeline immediately — matching Forge's existing
    `decide_step` semantics exactly."""
    rec = _get_recommendation(db, tenant_id, recommendation_id)
    if rec.approval_instance_id is None:
        raise ValueError(f"Recommendation {recommendation_id} has not started validation yet.")

    current_stage = rec.status if rec.status in VALIDATION_STAGES else VALIDATION_STAGES[0]
    instance = forge_approval_service.decide_step(
        db, rec.approval_instance_id, decided_by=decided_by, decided_role=decided_role, decision=decision, notes=notes,
    )

    if decision == "rejected":
        rec.status = "rejected"
    elif instance["status"] == "approved":
        rec.status = VALIDATION_STAGES[-1]
    else:
        rec.status = VALIDATION_STAGES[instance["current_step_index"]]
    db.commit()
    db.refresh(rec)

    outcome = ValidationOutcome(
        tenant_id=tenant_id, recommendation_id=recommendation_id, stage=current_stage,
        outcome_notes=outcome_notes, lessons_learned=lessons_learned, measured_impact=measured_impact,
        recorded_by=decided_by,
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)

    return {"recommendation_status": rec.status, "instance": instance, "outcome_id": outcome.id}


def record_outcome(
    db: Session, tenant_id: str, recommendation_id: int, *, stage: str, outcome_notes: str = "",
    lessons_learned: str = "", measured_impact: str = "", recorded_by: str = "",
) -> dict:
    if stage not in VALIDATION_STAGES:
        raise ValueError(f"stage must be one of {VALIDATION_STAGES}")
    _get_recommendation(db, tenant_id, recommendation_id)  # existence check
    row = ValidationOutcome(
        tenant_id=tenant_id, recommendation_id=recommendation_id, stage=stage, outcome_notes=outcome_notes,
        lessons_learned=lessons_learned, measured_impact=measured_impact, recorded_by=recorded_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id, "stage": row.stage, "outcome_notes": row.outcome_notes,
        "lessons_learned": row.lessons_learned, "measured_impact": row.measured_impact,
    }


def list_outcomes(db: Session, tenant_id: str, recommendation_id: int) -> list[dict]:
    rows = (
        db.query(ValidationOutcome)
        .filter(ValidationOutcome.tenant_id == tenant_id, ValidationOutcome.recommendation_id == recommendation_id)
        .order_by(ValidationOutcome.created_at.asc())
        .all()
    )
    return [
        {
            "id": r.id, "stage": r.stage, "outcome_notes": r.outcome_notes, "lessons_learned": r.lessons_learned,
            "measured_impact": r.measured_impact, "recorded_by": r.recorded_by, "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


def get_validation_status(db: Session, tenant_id: str, recommendation_id: int) -> dict:
    rec = _get_recommendation(db, tenant_id, recommendation_id)
    instance = forge_approval_service.get_instance(db, rec.approval_instance_id) if rec.approval_instance_id else None
    return {
        "recommendation_id": rec.id, "status": rec.status, "instance": instance,
        "outcomes": list_outcomes(db, tenant_id, recommendation_id),
        "human_review_required": True, "disclaimer": DISCLAIMER,
    }
