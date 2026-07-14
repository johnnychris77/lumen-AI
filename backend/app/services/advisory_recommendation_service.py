"""Advisor — Phase 7 §1/§3/§4: Advisory Mode recommendation presentation
and technician interaction logging.

Reuses ``app.services.ml.explainability.explain_prediction()`` directly
for the presentation contract (Section 3's exact field list — supported
finding, confidence, model version, image quality, known limitations,
human review requirement) rather than building a second one. Adds only
what Section 3 additionally asks for that the pinned Genesis contract
doesn't carry: an evidence summary, an explicit non-definitive disclaimer,
and — genuinely new — whether the model abstained (reused
``error_analysis.LOW_CONFIDENCE_THRESHOLD``, not a new tunable).

Interaction logging (§4) is the technician-facing counterpart to
``SupervisorReview`` — a distinct actor, a distinct table
(``AdvisoryRecommendationInteraction``), never conflated with the
supervisor's own review.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.advisory_pilot import AdvisoryRecommendationInteraction
from app.services import workflow_state_service
from app.services.ml.error_analysis import LOW_CONFIDENCE_THRESHOLD
from app.services.ml.explainability import explain_prediction

RECOMMENDATION_DISCLAIMER = (
    "This is an AI-generated recommendation, not a definitive conclusion. "
    "A qualified human reviewer must confirm any finding before action is taken."
)

DECISIONS = ("accepted", "modified", "rejected")


def present_recommendation(
    *, predicted_class: str, confidence: float, model_version: str,
    image_quality: str, supported_classes: list[str], evidence_summary: str = "",
) -> dict[str, Any]:
    """§3 — the full recommendation presentation, never shown as a
    definitive conclusion."""
    base = explain_prediction(
        predicted_class=predicted_class, confidence=confidence, model_version=model_version,
        image_quality=image_quality, supported_classes=supported_classes,
    )
    return {
        **base,
        "evidence_summary": evidence_summary,
        "abstained": confidence < LOW_CONFIDENCE_THRESHOLD or base["supported_class"] is None,
        "recommendation_disclaimer": RECOMMENDATION_DISCLAIMER,
    }


def _time_to_decision_seconds(db: Session, tenant_id: str, inspection_id: int) -> float | None:
    """Seconds from the inspection's AI_ANALYSIS workflow event to now —
    reuses the existing WorkflowStateEvent log rather than a new stopwatch
    field. None if no AI_ANALYSIS event has been recorded yet."""
    events = workflow_state_service.state_history(db, inspection_id)
    analysis_events = [e for e in events if e.to_state == workflow_state_service.AI_ANALYSIS]
    if not analysis_events:
        return None
    started = workflow_state_service.aware_utc(analysis_events[-1].created_at)
    now = datetime.now(timezone.utc)
    return round((now - started).total_seconds(), 3)


def record_interaction(
    db: Session, *, tenant_id: str, inspection_id: int, model_id: str = "", model_version: str = "",
    predicted_label: str, confidence: float | None, decision: str, modified_to: str = "",
    reason_for_rejection: str = "", reviewer_comments: str = "", user_confidence_rating: int | None = None,
    decided_by: str, decided_role: str = "",
) -> AdvisoryRecommendationInteraction:
    if decision not in DECISIONS:
        raise ValueError(f"Unknown decision '{decision}'. Must be one of {DECISIONS}.")
    row = AdvisoryRecommendationInteraction(
        tenant_id=tenant_id, inspection_id=inspection_id, model_id=model_id, model_version=model_version,
        predicted_label=predicted_label, confidence=confidence, decision=decision, modified_to=modified_to,
        reason_for_rejection=reason_for_rejection, reviewer_comments=reviewer_comments,
        user_confidence_rating=user_confidence_rating, decided_by=decided_by, decided_role=decided_role,
        time_to_decision_seconds=_time_to_decision_seconds(db, tenant_id, inspection_id),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_interactions(db: Session, tenant_id: str, *, model_id: str | None = None) -> list[AdvisoryRecommendationInteraction]:
    q = db.query(AdvisoryRecommendationInteraction).filter(AdvisoryRecommendationInteraction.tenant_id == tenant_id)
    if model_id:
        q = q.filter(AdvisoryRecommendationInteraction.model_id == model_id)
    return q.order_by(AdvisoryRecommendationInteraction.id.desc()).all()
