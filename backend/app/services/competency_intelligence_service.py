"""v2.9 — LumenAI Quality (Project Guardian), Section 7: Competency
Intelligence.

Derives coaching/education opportunities from the existing `CompetencyEvent`
log (`competency_service.py`) rather than creating a second event log.
Individual repeated errors suggest one-on-one coaching; the same finding
type recurring across several technicians suggests team education; a
department-wide pattern suggests retraining. Effectiveness is measured by
comparing each technician's repeated-error rate before and after the
opportunity was raised — nothing is fabricated for a technician with no
recorded activity in one of the two windows.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.competency_event import CompetencyEvent
from app.models.quality_guardian import (
    OPPORTUNITY_COACHING,
    OPPORTUNITY_DEPARTMENT_RETRAINING,
    OPPORTUNITY_TEAM_EDUCATION,
    CompetencyOpportunity,
)

_INDIVIDUAL_THRESHOLD = 2
_TEAM_THRESHOLD = 3
_DEPARTMENT_THRESHOLD = 5


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _already_open(db: Session, tenant_id: str, *, scope_type: str, scope_value: str, opportunity_type: str, finding_type: str) -> bool:
    return (
        db.query(CompetencyOpportunity.id)
        .filter(
            CompetencyOpportunity.tenant_id == tenant_id, CompetencyOpportunity.scope_type == scope_type,
            CompetencyOpportunity.scope_value == scope_value, CompetencyOpportunity.opportunity_type == opportunity_type,
            CompetencyOpportunity.finding_type == finding_type, CompetencyOpportunity.status == "open",
        )
        .first()
        is not None
    )


def detect_competency_opportunities(db: Session, tenant_id: str) -> list[dict]:
    repeated = (
        db.query(CompetencyEvent)
        .filter(CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.event_type == "repeated_error")
        .all()
    )

    by_technician_finding: dict[tuple[str, str], int] = {}
    by_finding_technicians: dict[str, set[str]] = {}
    for e in repeated:
        key = (e.technician, e.finding_type)
        by_technician_finding[key] = by_technician_finding.get(key, 0) + 1
        by_finding_technicians.setdefault(e.finding_type, set()).add(e.technician)

    created: list[CompetencyOpportunity] = []

    for (technician, finding_type), count in by_technician_finding.items():
        if count >= _INDIVIDUAL_THRESHOLD and not _already_open(
            db, tenant_id, scope_type="individual", scope_value=technician,
            opportunity_type=OPPORTUNITY_COACHING, finding_type=finding_type,
        ):
            row = CompetencyOpportunity(
                tenant_id=tenant_id, scope_type="individual", scope_value=technician,
                opportunity_type=OPPORTUNITY_COACHING, finding_type=finding_type,
                rationale=f"{technician} has {count} repeated-error events on '{finding_type}' findings.",
            )
            db.add(row)
            created.append(row)

    for finding_type, technicians in by_finding_technicians.items():
        if len(technicians) >= _DEPARTMENT_THRESHOLD and not _already_open(
            db, tenant_id, scope_type="department", scope_value="all",
            opportunity_type=OPPORTUNITY_DEPARTMENT_RETRAINING, finding_type=finding_type,
        ):
            row = CompetencyOpportunity(
                tenant_id=tenant_id, scope_type="department", scope_value="all",
                opportunity_type=OPPORTUNITY_DEPARTMENT_RETRAINING, finding_type=finding_type,
                rationale=f"{len(technicians)} technicians have repeated-error events on '{finding_type}' — "
                          "a department-wide pattern.",
            )
            db.add(row)
            created.append(row)
        elif len(technicians) >= _TEAM_THRESHOLD and not _already_open(
            db, tenant_id, scope_type="team", scope_value=finding_type,
            opportunity_type=OPPORTUNITY_TEAM_EDUCATION, finding_type=finding_type,
        ):
            row = CompetencyOpportunity(
                tenant_id=tenant_id, scope_type="team", scope_value=finding_type,
                opportunity_type=OPPORTUNITY_TEAM_EDUCATION, finding_type=finding_type,
                rationale=f"{len(technicians)} technicians have repeated-error events on '{finding_type}'.",
            )
            db.add(row)
            created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)
    return [_row_to_dict(r) for r in created]


def list_opportunities(db: Session, tenant_id: str, *, status: str = "") -> list[dict]:
    q = db.query(CompetencyOpportunity).filter(CompetencyOpportunity.tenant_id == tenant_id)
    if status:
        q = q.filter(CompetencyOpportunity.status == status)
    rows = q.order_by(CompetencyOpportunity.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def mark_addressed(db: Session, tenant_id: str, opportunity_id: int) -> dict | None:
    row = (
        db.query(CompetencyOpportunity)
        .filter(CompetencyOpportunity.id == opportunity_id, CompetencyOpportunity.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        return None
    row.status = "addressed"
    row.addressed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def track_effectiveness(db: Session, tenant_id: str, opportunity_id: int) -> dict | None:
    """Compares repeated-error rate for this opportunity's scope before and
    after it was addressed. Returns None (not a fabricated 0) when either
    window has no recorded activity to compare."""
    row = (
        db.query(CompetencyOpportunity)
        .filter(CompetencyOpportunity.id == opportunity_id, CompetencyOpportunity.tenant_id == tenant_id)
        .first()
    )
    if row is None or row.addressed_at is None:
        return None

    def _rate(before: bool) -> float | None:
        q = db.query(CompetencyEvent).filter(
            CompetencyEvent.tenant_id == tenant_id, CompetencyEvent.finding_type == row.finding_type,
        )
        if row.scope_type == "individual":
            q = q.filter(CompetencyEvent.technician == row.scope_value)
        q = q.filter(CompetencyEvent.created_at < row.addressed_at) if before else q.filter(CompetencyEvent.created_at >= row.addressed_at)
        events = q.all()
        if not events:
            return None
        repeats = sum(1 for e in events if e.event_type == "repeated_error")
        return repeats / len(events)

    before_rate = _rate(before=True)
    after_rate = _rate(before=False)
    if before_rate is None or after_rate is None:
        return None

    effectiveness = round((before_rate - after_rate) * 100, 1)
    row.effectiveness_score = effectiveness
    db.commit()
    db.refresh(row)
    result = _row_to_dict(row)
    result["before_repeated_error_rate"] = round(before_rate, 3)
    result["after_repeated_error_rate"] = round(after_rate, 3)
    return result
