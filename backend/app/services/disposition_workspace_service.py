"""v1.6 — Supervisor Disposition Workspace service (Deliverable 6)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.disposition_override import DISPOSITION_ACTIONS, DispositionOverride

_REASON_REQUIRED_ACTIONS = {a for a in DISPOSITION_ACTIONS if a != "approve"}


class InvalidDispositionAction(ValueError):
    pass


class ReasonRequiredError(ValueError):
    pass


def submit_disposition_action(
    db: Session, *, tenant_id: str, inspection_id: int, reviewer_name: str, reviewer_role: str,
    action: str, ai_recommended_disposition: str, modified_disposition: str = "", reason: str = "",
) -> DispositionOverride:
    if action not in DISPOSITION_ACTIONS:
        raise InvalidDispositionAction(f"action must be one of {DISPOSITION_ACTIONS}")
    if action in _REASON_REQUIRED_ACTIONS and not reason.strip():
        raise ReasonRequiredError(f"A reason is required for action '{action}'.")

    row = DispositionOverride(
        inspection_id=inspection_id,
        tenant_id=tenant_id,
        reviewer_name=reviewer_name,
        reviewer_role=reviewer_role,
        action=action,
        ai_recommended_disposition=ai_recommended_disposition,
        modified_disposition=modified_disposition.strip(),
        reason=reason.strip(),
    )
    db.add(row)
    return row


def list_disposition_actions(db: Session, tenant_id: str, inspection_id: int) -> list[DispositionOverride]:
    return (
        db.query(DispositionOverride)
        .filter(DispositionOverride.tenant_id == tenant_id, DispositionOverride.inspection_id == inspection_id)
        .order_by(DispositionOverride.id.desc())
        .all()
    )
