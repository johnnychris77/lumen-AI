"""v3.5 — Project Beacon, Section 10: Industry Advisory Board Module.

Board membership reuses P24's `AdvisoryConsortiumMember` directly (via
`beacon_collaboration_hub_service`) — a member roster, not a meeting
tracker, so this module adds the three tables that genuinely don't exist
anywhere else in this codebase: `AdvisoryBoardMeeting`,
`AdvisoryBoardActionItem`, `AdvisoryBoardRecommendation`
(`app/models/industry_collaboration.py`). Every recommendation is
advisory only (`human_review_required: true`) and is never auto-applied
to any product roadmap or local system.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.industry_collaboration import (
    ACTION_OPEN,
    DISCLAIMER,
    MEETING_SCHEDULED,
    RECOMMENDATION_PROPOSED,
    AdvisoryBoardActionItem,
    AdvisoryBoardMeeting,
    AdvisoryBoardRecommendation,
)
from app.services import beacon_collaboration_hub_service


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def board_members(db: Session) -> list[dict]:
    return beacon_collaboration_hub_service.collaboration_hub_summary(db)["participants_by_type"]


def schedule_meeting(db: Session, *, title: str, scheduled_at: datetime, attendee_organizations: list[str]) -> dict:
    meeting = AdvisoryBoardMeeting(
        title=title, scheduled_at=scheduled_at, status=MEETING_SCHEDULED,
        attendee_organizations=json.dumps(attendee_organizations),
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return _row_to_dict(meeting)


def record_meeting_notes(db: Session, meeting_id: int, *, meeting_notes: str, roadmap_feedback: str = "", recorded_by: str = "") -> dict | None:
    meeting = db.query(AdvisoryBoardMeeting).filter(AdvisoryBoardMeeting.id == meeting_id).first()
    if meeting is None:
        return None
    meeting.meeting_notes = meeting_notes
    meeting.roadmap_feedback = roadmap_feedback
    meeting.recorded_by = recorded_by
    meeting.status = "completed"
    db.commit()
    db.refresh(meeting)
    return _row_to_dict(meeting)


def list_meetings(db: Session) -> list[dict]:
    rows = db.query(AdvisoryBoardMeeting).order_by(AdvisoryBoardMeeting.scheduled_at.desc()).all()
    return [_row_to_dict(r) for r in rows]


def add_action_item(db: Session, meeting_id: int, *, description: str, owner: str = "", due_date: datetime | None = None) -> dict:
    item = AdvisoryBoardActionItem(meeting_id=meeting_id, description=description, owner=owner, due_date=due_date, status=ACTION_OPEN)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _row_to_dict(item)


def resolve_action_item(db: Session, item_id: int) -> dict | None:
    item = db.query(AdvisoryBoardActionItem).filter(AdvisoryBoardActionItem.id == item_id).first()
    if item is None:
        return None
    item.status = "done"
    item.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return _row_to_dict(item)


def list_action_items(db: Session, *, meeting_id: int | None = None, status: str = "") -> list[dict]:
    q = db.query(AdvisoryBoardActionItem)
    if meeting_id is not None:
        q = q.filter(AdvisoryBoardActionItem.meeting_id == meeting_id)
    if status:
        q = q.filter(AdvisoryBoardActionItem.status == status)
    return [_row_to_dict(r) for r in q.order_by(AdvisoryBoardActionItem.id.desc()).all()]


def propose_recommendation(db: Session, *, title: str, rationale: str, target_area: str, meeting_id: int | None = None, review_cycle: str = "") -> dict:
    rec = AdvisoryBoardRecommendation(
        title=title, rationale=rationale, target_area=target_area, meeting_id=meeting_id,
        review_cycle=review_cycle, status=RECOMMENDATION_PROPOSED,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return _row_to_dict(rec)


def decide_recommendation(db: Session, recommendation_id: int, *, status: str, decided_by: str) -> dict | None:
    if status not in ("adopted", "declined", "under_review"):
        raise ValueError("status must be one of adopted/declined/under_review")
    rec = db.query(AdvisoryBoardRecommendation).filter(AdvisoryBoardRecommendation.id == recommendation_id).first()
    if rec is None:
        return None
    rec.status = status
    rec.decided_by = decided_by
    rec.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)
    return _row_to_dict(rec)


def list_recommendations(db: Session, *, status: str = "") -> list[dict]:
    q = db.query(AdvisoryBoardRecommendation)
    if status:
        q = q.filter(AdvisoryBoardRecommendation.status == status)
    return [_row_to_dict(r) for r in q.order_by(AdvisoryBoardRecommendation.id.desc()).all()]


def advisory_board_summary(db: Session) -> dict:
    return {
        "members": board_members(db),
        "meetings": list_meetings(db),
        "open_action_items": list_action_items(db, status=ACTION_OPEN),
        "recommendations": list_recommendations(db),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
