"""v4.1 — Project Forge, Section 10: Forge Marketplace.

Reuses the exact same `WorkflowDefinition` model Sections 1 and 4
already use — `marketplace_status` (private/pending_review/published) is
just one more field on that model, not a second workflow-library table.
"Community templates require governance approval" is enforced by
`marketplace_status` starting at `pending_review` when a tenant shares a
workflow, and only ever becoming `published` (visible to every tenant)
through `approve_share`, gated to the `admin` role at the route layer —
the same draft → review → published idiom Beacon's
`StandardsPublication` and P24's `AdvisoryConsortiumMember` already
established for governance-gated content in this codebase.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.workflow_forge import (
    MARKETPLACE_PENDING_REVIEW,
    MARKETPLACE_PRIVATE,
    MARKETPLACE_PUBLISHED,
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    WorkflowDefinition,
)
from app.services.forge_workflow_service import UnknownWorkflowError, get_workflow_row_or_404


class NotShareableError(Exception):
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


def list_marketplace(db: Session) -> list[dict]:
    rows = db.query(WorkflowDefinition).filter(
        WorkflowDefinition.marketplace_status == MARKETPLACE_PUBLISHED, WorkflowDefinition.is_current.is_(True),
    ).order_by(WorkflowDefinition.id.desc()).all()
    return [_row_to_dict(r) for r in rows]


def clone_workflow(db: Session, tenant_id: str, workflow_id: int, *, cloned_by: str, new_name: str | None = None) -> dict:
    """Clones any workflow (a tenant's own, a template, or a published
    marketplace listing) into a brand-new draft owned by `tenant_id` —
    a new `workflow_ref` (it is not a version of the source, it is its
    own independent workflow from here on)."""
    source = get_workflow_row_or_404(db, workflow_id)
    new_row = WorkflowDefinition(
        tenant_id=tenant_id, workflow_ref=_new_ref(), name=new_name or f"{source.name} (copy)",
        description=source.description, category=source.category, nodes_json=source.nodes_json,
        edges_json=source.edges_json, version=1, status=STATUS_DRAFT, is_current=True, author=cloned_by,
        marketplace_status=MARKETPLACE_PRIVATE,
    )
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return _row_to_dict(new_row)


def import_template(db: Session, tenant_id: str, category: str, *, imported_by: str) -> dict:
    from app.services.forge_template_service import get_template
    template = get_template(db, category)
    if template is None:
        raise UnknownWorkflowError(f"No template found for category '{category}'.")
    return clone_workflow(db, tenant_id, template["id"], cloned_by=imported_by, new_name=template["name"])


def share_workflow(db: Session, workflow_id: int, *, shared_by: str) -> dict:
    """Submits a tenant's own workflow to the marketplace for governance
    review — never publishes it directly."""
    row = get_workflow_row_or_404(db, workflow_id)
    if row.status != STATUS_PUBLISHED:
        raise NotShareableError("Only a published workflow can be shared to the marketplace.")
    row.marketplace_status = MARKETPLACE_PENDING_REVIEW
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def approve_share(db: Session, workflow_id: int, *, approved_by: str) -> dict:
    row = get_workflow_row_or_404(db, workflow_id)
    if row.marketplace_status != MARKETPLACE_PENDING_REVIEW:
        raise NotShareableError(f"Workflow {workflow_id} is not pending marketplace review.")
    row.marketplace_status = MARKETPLACE_PUBLISHED
    row.approved_by = approved_by
    row.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def export_workflow(db: Session, workflow_id: int) -> dict:
    """Returns a portable JSON blob of a workflow's nodes/edges/metadata
    — the literal export artifact Section 10 asks for."""
    row = get_workflow_row_or_404(db, workflow_id)
    return {
        "workflow_ref": row.workflow_ref, "name": row.name, "description": row.description,
        "category": row.category, "version": row.version, "nodes": json.loads(row.nodes_json),
        "edges": json.loads(row.edges_json), "exported_at": datetime.now(timezone.utc).isoformat(),
    }
