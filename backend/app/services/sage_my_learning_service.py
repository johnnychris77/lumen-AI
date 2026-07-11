"""Project Sage, Section 11: Technician Learning Center (`/my-learning`).

Returns only the authenticated user's own authorized learning information --
never a peer's. The route layer is responsible for passing the actual
authenticated identity as `learner`; this service never accepts an arbitrary
"which technician" parameter from the request body, only the resolved
identity, so there is no way to request someone else's data through this
function's signature.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.competency_service import competency_summary
from app.services.sage_assessment_service import list_assessments
from app.services.sage_learning_plan_service import list_plans_for_learner


def my_learning_center(db: Session, tenant_id: str, learner: str) -> dict:
    plans = list_plans_for_learner(db, tenant_id, learner)
    assessments = list_assessments(db, tenant_id, target_learner=learner)
    competency = competency_summary(db, learner)

    return {
        "learner": learner,
        "assigned_modules": [p for p in plans if p["completion_status"] in ("assigned", "in_progress")],
        "completed_education": [p for p in plans if p["completion_status"] == "completed"],
        "due_dates": [{"learning_plan_id": p["id"], "due_date": p["due_date"]} for p in plans if p["due_date"]],
        "competency_status": competency,
        "assessments": assessments,
        "supervisor_feedback": [p["override_reason"] for p in plans if p["override_reason"]],
    }
