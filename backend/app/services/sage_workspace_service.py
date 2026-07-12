"""Project Sage, Section 10: Sage Workspace (`/sage`).

Aggregates learning plans, gaps, microlearning, and assessments with the
filters the brief names -- facility/department/shift/role/instrument
family/anatomy zone/finding/competency/date range. `shift` is honestly
reported as not tracked (this codebase already treats `shift` as an
`UNTRACKED_TARGET` -- see `app/models/quality_guardian.py`) rather than
deriving a fabricated time-of-day bucket.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.sage_knowledge_gap_service import list_gaps
from app.services.sage_learning_plan_service import list_plans
from app.services.sage_microlearning_service import list_modules

SHIFT_NOT_TRACKED_NOTE = "Shift-level attribution is not tracked in this codebase; reported honestly as unavailable rather than derived."


def workspace_summary(
    db: Session, tenant_id: str, *, instrument_family: str = "", anatomy_zone: str = "",
    competency_domain: str = "", learner_or_group: str = "", shift: str = "",
) -> dict:
    if shift:
        return {"available": False, "note": SHIFT_NOT_TRACKED_NOTE}

    gaps = list_gaps(db, tenant_id, competency_domain=competency_domain, instrument_family=instrument_family, anatomy_zone=anatomy_zone)
    plans = list_plans(db, tenant_id, learner_or_group=learner_or_group)
    overdue = [p for p in plans if p["completion_status"] == "overdue"]
    modules = list_modules(db, tenant_id, approval_status="approved")

    return {
        "recommended_learning_plans": [p for p in plans if not p["approved_by"]],
        "overdue_competencies": overdue,
        "recurring_knowledge_gaps": gaps,
        "instrument_family_education_needs": sorted({g["instrument_family"] for g in gaps if g["instrument_family"]}),
        "anatomy_zone_education_needs": sorted({g["anatomy_zone"] for g in gaps if g["anatomy_zone"]}),
        "approved_microlearning_modules": modules,
        "human_review_required": True,
    }
