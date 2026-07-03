"""Phase 22 §8 — Supervisor Agent.

Reports whether a human supervisor has already reviewed this inspection —
agreement, corrections, override, and whether a training label (Phase 18
PilotValidationCase) exists. This agent never fabricates or simulates a
supervisor decision: only a human submitting
POST /inspections/{id}/supervisor-review creates one (Design Principle 4 —
human expertise is the final authority). The agent is read-only.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.context import SupervisorContext
from app.models.pilot_validation import PilotValidationCase
from app.models.supervisor_review import SupervisorReview


class SupervisorAgent:
    NAME = "Supervisor Agent"
    VERSION = "1.0.0"
    CAPABILITIES = ["report_supervisor_review_status", "report_training_label_status"]
    DEPENDS_ON = ["RecommendationAgent"]

    def run(self, db: Session, inspection_id: int, tenant_id: str) -> SupervisorContext:
        # Labels are tenant-scoped, but /api/pilot-validation/cases accepts an
        # arbitrary inspection_id in its payload — without the tenant filter
        # here, a case recorded (or mistakenly imported) by another tenant
        # against the same inspection_id could leak that tenant's
        # ground-truth label into this inspection's context.
        review = (
            db.query(SupervisorReview)
            .filter(SupervisorReview.inspection_id == inspection_id, SupervisorReview.tenant_id == tenant_id)
            .order_by(SupervisorReview.id.desc())
            .first()
        )
        case = (
            db.query(PilotValidationCase)
            .filter(PilotValidationCase.inspection_id == inspection_id, PilotValidationCase.tenant_id == tenant_id)
            .order_by(PilotValidationCase.id.desc())
            .first()
        )
        if review is None:
            return SupervisorContext(review_exists=False, training_label_created=case is not None)

        corrections = {}
        if review.corrected_zone:
            corrections["zone"] = review.corrected_zone
        if review.corrected_instrument_family:
            corrections["instrument_family"] = review.corrected_instrument_family
        if review.corrected_severity:
            corrections["severity"] = review.corrected_severity
        if review.corrected_recommendation:
            corrections["recommendation"] = review.corrected_recommendation

        return SupervisorContext(
            review_exists=True,
            agreement=review.agreement,
            corrections=corrections,
            override_action=review.override_action,
            ground_truth_label=case.ground_truth_label if case else None,
            training_label_created=case is not None,
        )
