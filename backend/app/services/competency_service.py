"""v1.4 — Technician competency support.

Records competency events (findings reviewed, supervisor corrections, repeated
errors, education completed) and builds per-technician competency summaries.
Repeated-error detection and training progress are both derived only from
events actually recorded — nothing is fabricated for technicians with no
recorded activity.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.competency_event import CompetencyEvent

# A finding-type correction recorded this many times (or more) for the same
# technician is flagged as a repeated error.
_REPEATED_ERROR_THRESHOLD = 2


def _record(db: Session, *, tenant_id: str, technician: str, event_type: str,
            finding_type: str = "", inspection_id: int | None = None) -> CompetencyEvent:
    event = CompetencyEvent(
        tenant_id=tenant_id,
        technician=technician,
        event_type=event_type,
        finding_type=finding_type,
        inspection_id=inspection_id,
    )
    db.add(event)
    return event


def record_finding_reviewed(db: Session, *, tenant_id: str, technician: str, inspection_id: int) -> None:
    """A supervisor reviewed one of this technician's inspections."""
    if not technician:
        return
    _record(db, tenant_id=tenant_id, technician=technician,
            event_type="finding_reviewed", inspection_id=inspection_id)


def record_supervisor_correction(db: Session, *, tenant_id: str, technician: str,
                                  finding_type: str, inspection_id: int) -> None:
    """A supervisor disagreed with, partially agreed with, or overrode the AI
    on one of this technician's inspections. Also detects and logs a repeated
    error when the same technician has been corrected on the same finding
    type before."""
    if not technician:
        return
    _record(db, tenant_id=tenant_id, technician=technician,
            event_type="supervisor_correction", finding_type=finding_type,
            inspection_id=inspection_id)

    if not finding_type:
        return
    prior_corrections = (
        db.query(func.count(CompetencyEvent.id))
        .filter(
            CompetencyEvent.technician == technician,
            CompetencyEvent.event_type == "supervisor_correction",
            CompetencyEvent.finding_type == finding_type,
        )
        .scalar()
        or 0
    )
    if prior_corrections >= _REPEATED_ERROR_THRESHOLD:
        _record(db, tenant_id=tenant_id, technician=technician,
                event_type="repeated_error", finding_type=finding_type,
                inspection_id=inspection_id)


def record_education_completed(db: Session, *, tenant_id: str, technician: str, finding_type: str) -> None:
    if not technician:
        return
    _record(db, tenant_id=tenant_id, technician=technician,
            event_type="education_completed", finding_type=finding_type)


def _count(db: Session, technician: str, event_type: str) -> int:
    return (
        db.query(func.count(CompetencyEvent.id))
        .filter(CompetencyEvent.technician == technician, CompetencyEvent.event_type == event_type)
        .scalar()
        or 0
    )


def competency_summary(db: Session, technician: str) -> dict:
    """Per-technician competency summary derived entirely from recorded
    competency events — an empty summary for a technician with no recorded
    activity, never a fabricated score."""
    findings_reviewed = _count(db, technician, "finding_reviewed")
    supervisor_corrections = _count(db, technician, "supervisor_correction")

    repeated_error_rows = (
        db.query(CompetencyEvent.finding_type, func.count(CompetencyEvent.id))
        .filter(CompetencyEvent.technician == technician, CompetencyEvent.event_type == "repeated_error")
        .group_by(CompetencyEvent.finding_type)
        .all()
    )
    repeated_errors = {finding_type: count for finding_type, count in repeated_error_rows}

    education_rows = (
        db.query(CompetencyEvent.finding_type)
        .filter(CompetencyEvent.technician == technician, CompetencyEvent.event_type == "education_completed")
        .distinct()
        .all()
    )
    education_completed = sorted(row[0] for row in education_rows if row[0])

    # Training progress: a simple, honest ratio — corrections resolved without
    # becoming a repeated error, out of all recorded activity. None (not 0)
    # when there is no activity to score yet.
    total_activity = findings_reviewed + supervisor_corrections
    training_progress_pct = (
        round(100 * (1 - (sum(repeated_errors.values()) / supervisor_corrections)))
        if supervisor_corrections else None
    )

    return {
        "technician": technician,
        "findings_reviewed": findings_reviewed,
        "supervisor_corrections": supervisor_corrections,
        "repeated_errors": repeated_errors,
        "education_completed": education_completed,
        "training_progress_pct": training_progress_pct,
        "has_activity": total_activity > 0,
    }


# ── Technician Quality Dashboard (v1.5, Deliverable 5) ───────────────────────
def technician_quality_dashboard(db: Session, tenant_id: str) -> dict:
    """Per-technician quality rollup for leadership — inspection count,
    coverage quality, average AI confidence, supervisor agreement, repeat
    corrections, and training progress. Visible only to authorized roles;
    enforced by the route, not this function."""
    from app.db import models
    from app.models.supervisor_review import SupervisorReview

    rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.technician.isnot(None))
        .all()
    )
    by_technician: dict[str, list] = {}
    for r in rows:
        by_technician.setdefault(r.technician, []).append(r)

    technicians = []
    for technician, insp_rows in by_technician.items():
        coverage = [r.coverage_pct for r in insp_rows if r.coverage_pct is not None]
        confidences = [r.ai_confidence for r in insp_rows if r.has_image and r.ai_confidence is not None]

        insp_ids = [r.id for r in insp_rows]
        reviews = (
            db.query(SupervisorReview)
            .filter(SupervisorReview.inspection_id.in_(insp_ids))
            .all()
        ) if insp_ids else []
        agreement_pct = (
            round(100 * sum(1 for r in reviews if r.agreement == "agree") / len(reviews), 1)
            if reviews else None
        )

        summary = competency_summary(db, technician)

        technicians.append({
            "technician": technician,
            "inspection_count": len(insp_rows),
            "avg_coverage_pct": round(sum(coverage) / len(coverage), 1) if coverage else None,
            "avg_ai_confidence_pct": round(100 * sum(confidences) / len(confidences), 1) if confidences else None,
            "supervisor_agreement_pct": agreement_pct,
            "supervisor_corrections": summary["supervisor_corrections"],
            "repeated_errors": summary["repeated_errors"],
            "training_progress_pct": summary["training_progress_pct"],
        })

    technicians.sort(key=lambda t: t["inspection_count"], reverse=True)
    return {"technicians": technicians, "human_review_required": True}
