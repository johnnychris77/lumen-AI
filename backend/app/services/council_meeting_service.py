"""Project Council, Section 12: Council Meeting Mode.

Structured review agenda (case introduction, evidence review, specialist
assessments, dissent review, option comparison, human discussion notes,
decision, owner assignment, review date). `discussion_notes` and
`recorded_by` are always human-authored -- Council never presents its own
generated text as human meeting content, so `recorded_by` is required.
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.council_leadership import CouncilMeetingNotes

AGENDA_TEMPLATE = [
    "case_introduction", "evidence_review", "specialist_assessments", "dissent_review",
    "option_comparison", "human_discussion_notes", "decision", "owner_assignment", "review_date",
]


def to_dict(row: CouncilMeetingNotes) -> dict:
    return {
        "id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "council_case_id": row.council_case_id,
        "agenda": json.loads(row.agenda_json or "[]"),
        "discussion_notes": row.discussion_notes,
        "action_items": json.loads(row.action_items_json or "[]"),
        "owner": row.owner,
        "review_date": row.review_date.isoformat() if row.review_date else None,
        "recorded_by": row.recorded_by,
    }


def record_meeting_notes(
    db: Session, tenant_id: str, council_case_id: int, *, discussion_notes: str, recorded_by: str,
    action_items: list[str] | None = None, owner: str = "", review_date: datetime | None = None,
    agenda: list[str] | None = None,
) -> CouncilMeetingNotes:
    if not recorded_by.strip():
        raise ValueError("recorded_by is required -- Council meeting notes must be human-authored and attributed")

    row = CouncilMeetingNotes(
        tenant_id=tenant_id,
        council_case_id=council_case_id,
        agenda_json=json.dumps(agenda or AGENDA_TEMPLATE),
        discussion_notes=discussion_notes,
        action_items_json=json.dumps(action_items or []),
        owner=owner,
        review_date=review_date,
        recorded_by=recorded_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def meeting_notes_for_case(db: Session, tenant_id: str, council_case_id: int) -> list[dict]:
    rows = (
        db.query(CouncilMeetingNotes)
        .filter(CouncilMeetingNotes.tenant_id == tenant_id, CouncilMeetingNotes.council_case_id == council_case_id)
        .order_by(CouncilMeetingNotes.created_at.asc())
        .all()
    )
    return [to_dict(r) for r in rows]
