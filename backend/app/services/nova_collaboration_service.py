"""v5.4 — Project Nova, Section 7: Human-Agent Collaboration.

Users can assign tasks, approve or reject an agent's work, request an
explanation, or escalate to a supervisor. "Request explanations" reuses
GuardianX's `AIExplainabilityRecord`/`guardianx_explainability_service.py`
directly rather than a second explanation store -- an
`AgentCollaborationRequest` of type `request_explanation` simply
references the explainability record it triggered.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.nova_agent_platform import (
    COLLAB_APPROVED,
    COLLAB_COMPLETED,
    COLLAB_ESCALATED,
    COLLAB_PENDING,
    COLLAB_REJECTED,
    COLLABORATION_REQUEST_TYPES,
    COLLABORATION_STATUSES,
    AgentCollaborationRequest,
)


class UnknownCollaborationRequestError(Exception):
    pass


class InvalidCollaborationStateError(Exception):
    pass

_TERMINAL_STATUSES = (COLLAB_APPROVED, COLLAB_REJECTED, COLLAB_COMPLETED)


def _to_dict(row: AgentCollaborationRequest) -> dict:
    return {
        "id": row.id,
        "agent_key": row.agent_key,
        "tenant_id": row.tenant_id,
        "task_run_id": row.task_run_id,
        "request_type": row.request_type,
        "description": row.description,
        "requested_by": row.requested_by,
        "status": row.status,
        "resolution": row.resolution,
        "resolved_by": row.resolved_by,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "human_review_required": row.human_review_required,
        "created_at": row.created_at.isoformat(),
    }


def create_request(
    db: Session, agent_key: str, tenant_id: str, *, request_type: str, description: str = "",
    requested_by: str, task_run_id: int | None = None,
) -> dict:
    if request_type not in COLLABORATION_REQUEST_TYPES:
        raise ValueError(f"request_type must be one of {COLLABORATION_REQUEST_TYPES}")
    status = COLLAB_ESCALATED if request_type == "escalate_to_supervisor" else COLLAB_PENDING
    row = AgentCollaborationRequest(
        agent_key=agent_key, tenant_id=tenant_id, task_run_id=task_run_id, request_type=request_type,
        description=description, requested_by=requested_by, status=status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get_or_404(db: Session, request_id: int) -> AgentCollaborationRequest:
    row = db.query(AgentCollaborationRequest).filter(AgentCollaborationRequest.id == request_id).first()
    if row is None:
        raise UnknownCollaborationRequestError(f"Collaboration request {request_id} not found.")
    return row


def resolve_request(db: Session, request_id: int, *, decision: str, resolution: str = "", resolved_by: str) -> dict:
    row = _get_or_404(db, request_id)
    if row.status in _TERMINAL_STATUSES:
        raise InvalidCollaborationStateError(f"Collaboration request {request_id} is already '{row.status}'.")
    if decision not in COLLABORATION_STATUSES:
        raise ValueError(f"decision must be one of {COLLABORATION_STATUSES}")
    row.status = decision
    row.resolution = resolution
    row.resolved_by = resolved_by
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def get_request(db: Session, request_id: int) -> dict:
    return _to_dict(_get_or_404(db, request_id))


def list_requests(db: Session, tenant_id: str, *, agent_key: str = "", status: str = "") -> list[dict]:
    query = db.query(AgentCollaborationRequest).filter(AgentCollaborationRequest.tenant_id == tenant_id)
    if agent_key:
        query = query.filter(AgentCollaborationRequest.agent_key == agent_key)
    if status:
        query = query.filter(AgentCollaborationRequest.status == status)
    rows = query.order_by(AgentCollaborationRequest.created_at.desc()).all()
    return [_to_dict(r) for r in rows]
