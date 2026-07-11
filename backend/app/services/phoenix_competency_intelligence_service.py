"""v4.9 — Project Phoenix, Section 6: Competency Intelligence.

`competency_intelligence_service.py` (v2.9) already detects coaching/
team-education/department-retraining opportunities via the shared
`CompetencyOpportunity` model. Two of that model's five `OPPORTUNITY_TYPES`
— `annual_competency` and `recurring_learning` — were defined but never
produced by any detector. Phoenix adds detectors for those plus three new
types (`simulation`, `mentoring`, `knowledge_sharing`), all writing to the
same `CompetencyOpportunity` table — no second competency-opportunity
model.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.competency_event import CompetencyEvent
from app.models.quality_guardian import (
    OPPORTUNITY_ANNUAL_COMPETENCY,
    OPPORTUNITY_KNOWLEDGE_SHARING,
    OPPORTUNITY_MENTORING,
    OPPORTUNITY_RECURRING_LEARNING,
    OPPORTUNITY_SIMULATION,
    CompetencyOpportunity,
)
from app.services import competency_intelligence_service

_SIMULATION_FAILURE_THRESHOLD = 2
_ANNUAL_COMPETENCY_WINDOW_DAYS = 365
_RECURRING_LEARNING_WINDOW_DAYS = 90
_RECURRING_LEARNING_MIN_WINDOWS = 2
_MENTORING_MIN_CONTRIBUTIONS = 3


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _already_open(db: Session, tenant_id: str, *, scope_type: str, scope_value: str, opportunity_type: str) -> bool:
    return (
        db.query(CompetencyOpportunity.id)
        .filter(
            CompetencyOpportunity.tenant_id == tenant_id, CompetencyOpportunity.scope_type == scope_type,
            CompetencyOpportunity.scope_value == scope_value, CompetencyOpportunity.opportunity_type == opportunity_type,
            CompetencyOpportunity.status == "open",
        )
        .first()
        is not None
    )


def detect_simulation_opportunities(db: Session, tenant_id: str) -> list[dict]:
    """Technicians with repeated failed simulation scenarios (Apollo's
    `simulation_failed` CompetencyEvent, v4.7) — a real recurrence count."""
    rows = (
        db.query(CompetencyEvent)
        .filter(CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "simulation_failed")
        .all()
    )
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.technician] = counts.get(r.technician, 0) + 1

    created = []
    for technician, count in counts.items():
        if count >= _SIMULATION_FAILURE_THRESHOLD and not _already_open(
            db, tenant_id, scope_type="individual", scope_value=technician, opportunity_type=OPPORTUNITY_SIMULATION,
        ):
            row = CompetencyOpportunity(
                tenant_id=tenant_id, scope_type="individual", scope_value=technician,
                opportunity_type=OPPORTUNITY_SIMULATION,
                rationale=f"{technician} has {count} failed simulation scenarios recorded.",
            )
            db.add(row)
            created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return [_row_to_dict(r) for r in created]


def detect_annual_competency_due(db: Session, tenant_id: str) -> list[dict]:
    """Technicians with no `annual_competency` event in the last 365
    days — a real recency check, not a guessed due date."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=_ANNUAL_COMPETENCY_WINDOW_DAYS)
    all_technicians = {
        r.technician for r in db.query(CompetencyEvent).filter(CompetencyEvent.tenant_id == tenant_id).all()
    }
    recently_certified = {
        r.technician for r in db.query(CompetencyEvent).filter(
            CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "annual_competency",
            CompetencyEvent.created_at >= cutoff,
        ).all()
    }
    due = all_technicians - recently_certified

    created = []
    for technician in due:
        if not _already_open(db, tenant_id, scope_type="individual", scope_value=technician, opportunity_type=OPPORTUNITY_ANNUAL_COMPETENCY):
            row = CompetencyOpportunity(
                tenant_id=tenant_id, scope_type="individual", scope_value=technician,
                opportunity_type=OPPORTUNITY_ANNUAL_COMPETENCY,
                rationale=f"{technician} has no recorded annual competency within the last {_ANNUAL_COMPETENCY_WINDOW_DAYS} days.",
            )
            db.add(row)
            created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return [_row_to_dict(r) for r in created]


def detect_recurring_learning_needs(db: Session, tenant_id: str) -> list[dict]:
    """A technician with `repeated_error` events on the same finding type
    recurring across more than one 90-day window — a genuinely persistent
    pattern, not a single spike."""
    rows = (
        db.query(CompetencyEvent)
        .filter(CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "repeated_error")
        .all()
    )
    if not rows:
        return []

    windows: dict[tuple[str, str], set[int]] = {}
    earliest = min(r.created_at for r in rows)
    for r in rows:
        window_index = (r.created_at - earliest).days // _RECURRING_LEARNING_WINDOW_DAYS
        windows.setdefault((r.technician, r.finding_type), set()).add(window_index)

    created = []
    for (technician, finding_type), window_set in windows.items():
        if len(window_set) >= _RECURRING_LEARNING_MIN_WINDOWS and not _already_open(
            db, tenant_id, scope_type="individual", scope_value=technician, opportunity_type=OPPORTUNITY_RECURRING_LEARNING,
        ):
            row = CompetencyOpportunity(
                tenant_id=tenant_id, scope_type="individual", scope_value=technician,
                opportunity_type=OPPORTUNITY_RECURRING_LEARNING, finding_type=finding_type,
                rationale=f"{technician} has repeated-error events on '{finding_type}' across {len(window_set)} separate {_RECURRING_LEARNING_WINDOW_DAYS}-day windows.",
            )
            db.add(row)
            created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return [_row_to_dict(r) for r in created]


def detect_mentoring_and_knowledge_sharing(db: Session, tenant_id: str) -> list[dict]:
    """Pairs a high-contribution technician (potential mentor / knowledge
    source) with technicians who have open coaching opportunities
    (potential mentees) — both signals are real, already-recorded events."""
    contribution_counts: dict[str, int] = {}
    for r in db.query(CompetencyEvent).filter(
        CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "knowledge_contribution",
    ).all():
        contribution_counts[r.technician] = contribution_counts.get(r.technician, 0) + 1

    mentors = [t for t, c in contribution_counts.items() if c >= _MENTORING_MIN_CONTRIBUTIONS]
    coaching_open = competency_intelligence_service.list_opportunities(db, tenant_id, status="open")
    mentees = {o["scope_value"] for o in coaching_open if o["opportunity_type"] == "coaching"}

    created = []
    for mentor in mentors:
        if mentees and not _already_open(db, tenant_id, scope_type="individual", scope_value=mentor, opportunity_type=OPPORTUNITY_MENTORING):
            row = CompetencyOpportunity(
                tenant_id=tenant_id, scope_type="individual", scope_value=mentor,
                opportunity_type=OPPORTUNITY_MENTORING,
                rationale=f"{mentor} has {contribution_counts[mentor]} knowledge contributions and could mentor: {', '.join(sorted(mentees))}.",
            )
            db.add(row)
            created.append(row)
        if not _already_open(db, tenant_id, scope_type="individual", scope_value=mentor, opportunity_type=OPPORTUNITY_KNOWLEDGE_SHARING):
            row = CompetencyOpportunity(
                tenant_id=tenant_id, scope_type="individual", scope_value=mentor,
                opportunity_type=OPPORTUNITY_KNOWLEDGE_SHARING,
                rationale=f"{mentor}'s {contribution_counts[mentor]} knowledge contributions are candidates for formalizing into shared institutional knowledge.",
            )
            db.add(row)
            created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return [_row_to_dict(r) for r in created]


def run_all_detectors(db: Session, tenant_id: str) -> dict:
    """Runs every Phoenix + pre-existing competency detector and returns a
    combined summary — never auto-assigns training, only opens
    `CompetencyOpportunity` rows for human review."""
    existing = competency_intelligence_service.detect_competency_opportunities(db, tenant_id)
    return {
        "coaching_team_department": existing,
        "simulation": detect_simulation_opportunities(db, tenant_id),
        "annual_competency": detect_annual_competency_due(db, tenant_id),
        "recurring_learning": detect_recurring_learning_needs(db, tenant_id),
        "mentoring_and_knowledge_sharing": detect_mentoring_and_knowledge_sharing(db, tenant_id),
        "human_review_required": True,
    }
