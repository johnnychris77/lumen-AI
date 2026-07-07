"""v1.5 — Supervisor Quality Dashboard (Deliverable 6).

Per-supervisor review workload, override frequency, correction categories,
education provided, and AI agreement — derived from real SupervisorReview and
MentorCoachingReview rows. Department trends are derived from Inspection.department,
already captured at intake.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.db import models
from app.models.mentor_coaching_review import MentorCoachingReview
from app.models.supervisor_review import SupervisorReview


def _rate(n: int, d: int) -> float | None:
    return round(100 * n / d, 1) if d else None


def supervisor_quality_dashboard(db: Session, tenant_id: str) -> dict:
    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()
    coaching = db.query(MentorCoachingReview).filter(MentorCoachingReview.tenant_id == tenant_id).all()

    by_reviewer: dict[str, list] = defaultdict(list)
    for r in reviews:
        by_reviewer[r.reviewer_name].append(r)
    coaching_by_reviewer: dict[str, list] = defaultdict(list)
    for c in coaching:
        coaching_by_reviewer[c.reviewer_name].append(c)

    supervisors = []
    for reviewer, r_reviews in by_reviewer.items():
        override_ct = sum(1 for r in r_reviews if (r.override_action or "").strip())
        agree_ct = sum(1 for r in r_reviews if r.agreement == "agree")

        categories: dict[str, int] = defaultdict(int)
        for r in r_reviews:
            if r.corrected_zone:
                categories["zone"] += 1
            if r.corrected_instrument_family:
                categories["instrument_family"] += 1
            if r.corrected_severity:
                categories["severity"] += 1
            if r.corrected_recommendation:
                categories["recommendation"] += 1

        r_coaching = coaching_by_reviewer.get(reviewer, [])
        education_provided_ct = sum(1 for c in r_coaching if c.educational_comment.strip())

        supervisors.append({
            "reviewer": reviewer,
            "review_workload": len(r_reviews),
            "override_frequency_pct": _rate(override_ct, len(r_reviews)),
            "correction_categories": dict(categories),
            "education_provided_count": education_provided_ct,
            "agreement_with_ai_pct": _rate(agree_ct, len(r_reviews)),
        })

    supervisors.sort(key=lambda s: s["review_workload"], reverse=True)

    # Department trends — from Inspection.department, already captured at intake.
    insp_rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.department.isnot(None))
        .all()
    )
    by_department: dict[str, list] = defaultdict(list)
    for r in insp_rows:
        by_department[r.department or "unspecified"].append(r)

    departments = []
    for dept, dept_rows in by_department.items():
        scored = [r for r in dept_rows if r.has_image and r.disposition]
        total = len(scored)
        pass_ct = sum(1 for r in scored if r.disposition == "PASS")
        remove_ct = sum(1 for r in scored if r.disposition == "REMOVE FROM SERVICE")
        departments.append({
            "department": dept,
            "inspection_count": len(dept_rows),
            "pass_rate_pct": _rate(pass_ct, total),
            "remove_from_service_rate_pct": _rate(remove_ct, total),
        })
    departments.sort(key=lambda d: d["inspection_count"], reverse=True)

    return {
        "supervisors": supervisors,
        "department_trends": departments,
        "human_review_required": True,
    }
