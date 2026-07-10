"""v4.1 — Project Forge, Sections 1 & 9: Workflow Designer + Version Control.

CRUD for `WorkflowDefinition`, versioned with the exact pattern Beacon's
`beacon_standards_service.py` already established for `StandardsPublication`
— one nullable `supersedes_id` self-FK plus a `status` field, rather than
a second versioned-content model or a separate history table. A revision
never edits a published workflow in place: it creates a new row pointing
back via `supersedes_id`, and `is_current` moves to the new row.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.workflow_forge import (
    NODE_TYPES,
    STATUS_ARCHIVED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    WorkflowDefinition,
)


class UnknownWorkflowError(Exception):
    pass


class InvalidWorkflowStateError(Exception):
    pass


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    result["nodes"] = json.loads(result.pop("nodes_json") or "[]")
    result["edges"] = json.loads(result.pop("edges_json") or "[]")
    return result


def _new_ref() -> str:
    return f"WF-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:8].upper()}"


def _validate_nodes(nodes: list[dict]) -> None:
    for node in nodes:
        node_type = node.get("type")
        if node_type not in NODE_TYPES:
            raise ValueError(f"node type '{node_type}' must be one of {NODE_TYPES}")


def create_workflow(
    db: Session, tenant_id: str, *, name: str, description: str = "", category: str = "",
    nodes: list[dict], edges: list[dict], author: str,
) -> dict:
    _validate_nodes(nodes)
    row = WorkflowDefinition(
        tenant_id=tenant_id, workflow_ref=_new_ref(), name=name, description=description, category=category,
        nodes_json=json.dumps(nodes), edges_json=json.dumps(edges), version=1, status=STATUS_DRAFT,
        is_current=True, author=author,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def get_workflow_row_or_404(db: Session, workflow_id: int) -> WorkflowDefinition:
    row = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if row is None:
        raise UnknownWorkflowError(f"Workflow {workflow_id} not found.")
    return row


def get_workflow(db: Session, workflow_id: int) -> dict | None:
    row = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    return _row_to_dict(row) if row else None


def list_workflows(db: Session, tenant_id: str, *, category: str = "", current_only: bool = True) -> list[dict]:
    q = db.query(WorkflowDefinition).filter(
        (WorkflowDefinition.tenant_id == tenant_id) | (WorkflowDefinition.tenant_id == ""),
    )
    if category:
        q = q.filter(WorkflowDefinition.category == category)
    if current_only:
        q = q.filter(WorkflowDefinition.is_current.is_(True))
    return [_row_to_dict(r) for r in q.order_by(WorkflowDefinition.id.desc()).all()]


def revise_workflow(
    db: Session, workflow_id: int, *, updated_by: str, nodes: list[dict] | None = None,
    edges: list[dict] | None = None, name: str | None = None, description: str | None = None,
) -> dict:
    """A revision to an already-published workflow creates a new row
    (new version) and links the chain via `supersedes_id` — it never
    mutates a published workflow in place. A draft, not yet published,
    may simply be edited by calling this on itself only once published."""
    original = get_workflow_row_or_404(db, workflow_id)
    if nodes is not None:
        _validate_nodes(nodes)

    if original.status == STATUS_DRAFT:
        if nodes is not None:
            original.nodes_json = json.dumps(nodes)
        if edges is not None:
            original.edges_json = json.dumps(edges)
        if name is not None:
            original.name = name
        if description is not None:
            original.description = description
        original.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(original)
        return _row_to_dict(original)

    new_row = WorkflowDefinition(
        tenant_id=original.tenant_id, workflow_ref=original.workflow_ref,
        name=name if name is not None else original.name,
        description=description if description is not None else original.description,
        category=original.category,
        nodes_json=json.dumps(nodes) if nodes is not None else original.nodes_json,
        edges_json=json.dumps(edges) if edges is not None else original.edges_json,
        version=original.version + 1, status=STATUS_DRAFT, is_current=True,
        supersedes_id=original.id, author=updated_by, is_template=original.is_template,
    )
    original.is_current = False
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return _row_to_dict(new_row)


def publish_workflow(db: Session, workflow_id: int, *, approved_by: str) -> dict:
    row = get_workflow_row_or_404(db, workflow_id)
    if row.status == STATUS_PUBLISHED:
        raise InvalidWorkflowStateError(f"Workflow {workflow_id} is already published.")
    row.status = STATUS_PUBLISHED
    row.approved_by = approved_by
    row.approved_at = datetime.now(timezone.utc)
    row.effective_date = row.effective_date or datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def archive_workflow(db: Session, workflow_id: int) -> dict:
    row = get_workflow_row_or_404(db, workflow_id)
    row.status = STATUS_ARCHIVED
    row.is_current = False
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def version_history(db: Session, workflow_id: int) -> list[dict]:
    """Walks the `supersedes_id` chain to the root, then returns every
    version in order — same walk `beacon_standards_service.version_history`
    already established for `StandardsPublication`."""
    row = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if row is None:
        return []

    root_id = row.id
    seen: set[int] = set()
    while True:
        current = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == root_id).first()
        if current is None or not current.supersedes_id or current.supersedes_id in seen:
            break
        seen.add(current.supersedes_id)
        root_id = current.supersedes_id

    chain = []
    current_id: int | None = root_id
    visited: set[int] = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        current = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == current_id).first()
        if current is None:
            break
        chain.append(_row_to_dict(current))
        successor = db.query(WorkflowDefinition).filter(WorkflowDefinition.supersedes_id == current_id).first()
        current_id = successor.id if successor else None
    return chain


def rollback_to_version(db: Session, workflow_id: int, target_version_id: int, *, rolled_back_by: str) -> dict:
    """Section 9's 'Rollback' — republishes a prior version as the
    current one. The row being rolled back to keeps its own history
    (it is never deleted); the currently-current row is archived."""
    chain = version_history(db, workflow_id)
    chain_ids = {c["id"] for c in chain}
    if target_version_id not in chain_ids:
        raise InvalidWorkflowStateError(f"Version {target_version_id} is not part of workflow {workflow_id}'s version chain.")

    current = next((c for c in chain if c["is_current"]), None)
    target = get_workflow_row_or_404(db, target_version_id)

    if current is not None and current["id"] != target_version_id:
        current_row = get_workflow_row_or_404(db, current["id"])
        current_row.is_current = False
        current_row.status = STATUS_ARCHIVED

    target.is_current = True
    target.status = STATUS_PUBLISHED
    target.reviewer = rolled_back_by
    db.commit()
    db.refresh(target)
    return _row_to_dict(target)
