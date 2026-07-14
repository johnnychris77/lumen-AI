"""Dataset Registry & AI Model Development Foundation — Section 3.

A formal, validated 7-state annotation lifecycle, appended as an audited
event log (mirrors ``app.services.workflow_state_service``'s inspection
state machine: the current state is always the ``to_state`` of the latest
event, never a mutated single column, so the full labeling history is
always reconstructable). Distinct from ``RetainedImage.label_status``'s
simpler 4-value string (unlabeled/labeled/in_review/gold|rejected) — that
field is left untouched; this is the richer, audited lifecycle this
program's brief specifically asks for.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.dataset_governance import (
    ANNOTATION_STATES,
    ARCHIVED,
    UNLABELED,
    VALID_ANNOTATION_TRANSITIONS,
    AnnotationEvent,
    DatasetRegistryEntry,
)


class InvalidTransitionError(ValueError):
    def __init__(self, from_state: str, to_state: str):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Cannot transition annotation state from '{from_state}' to '{to_state}'.")


class UnknownStateError(ValueError):
    pass


def current_state(db: Session, dataset_entry_id: int) -> str:
    event = (
        db.query(AnnotationEvent)
        .filter(AnnotationEvent.dataset_entry_id == dataset_entry_id)
        .order_by(AnnotationEvent.id.desc())
        .first()
    )
    return event.to_state if event is not None else UNLABELED


def is_valid_transition(from_state: str, to_state: str) -> bool:
    return to_state in VALID_ANNOTATION_TRANSITIONS.get(from_state, set())


def transition(
    db: Session,
    *,
    tenant_id: str,
    dataset_entry_id: int,
    to_state: str,
    reviewer: str,
    confidence: float | None = None,
    comments: str = "",
    changes_json: str = "{}",
) -> AnnotationEvent:
    """Record a validated annotation-state transition. Raises
    ``InvalidTransitionError`` rather than silently accepting an
    out-of-order move (e.g. UNLABELED straight to APPROVED)."""
    if to_state not in ANNOTATION_STATES:
        raise UnknownStateError(f"Unknown annotation state '{to_state}'. Known: {ANNOTATION_STATES}")

    from_state = current_state(db, dataset_entry_id)
    if not is_valid_transition(from_state, to_state):
        raise InvalidTransitionError(from_state, to_state)

    event = AnnotationEvent(
        tenant_id=tenant_id,
        dataset_entry_id=dataset_entry_id,
        from_state=from_state,
        to_state=to_state,
        reviewer=reviewer,
        confidence=confidence,
        comments=comments,
        changes_json=changes_json,
    )
    db.add(event)

    entry = db.query(DatasetRegistryEntry).filter(DatasetRegistryEntry.id == dataset_entry_id).first()
    if entry is not None:
        entry.review_status = to_state
        entry.reviewer = reviewer or entry.reviewer
        if to_state != ARCHIVED:
            entry.annotation_version += 1

    db.commit()
    db.refresh(event)
    return event


def history(db: Session, dataset_entry_id: int) -> list[AnnotationEvent]:
    return (
        db.query(AnnotationEvent)
        .filter(AnnotationEvent.dataset_entry_id == dataset_entry_id)
        .order_by(AnnotationEvent.id.asc())
        .all()
    )
