"""v4.8 — Project Athena, Section 5: Clinical Playbooks.

Reuses Project Forge's `WorkflowDefinition`/`forge_workflow_service.py`
(v4.1) directly — a playbook is a `WorkflowDefinition` row with
`is_template=True` and `category` set to a clinical-scenario key. No
parallel playbook model. Decision trees are the existing `nodes_json`/
`edges_json`; version history and approval reuse Forge's existing
`version_history`/`publish_workflow` unchanged. Evidence/photos/videos
attach via `KnowledgeMediaAttachment` (source_type="workflow_definition");
standards attach via the new `linked_standards_json` column added to
`WorkflowDefinition` for this sprint.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.workflow_forge import WorkflowDefinition
from app.services import forge_workflow_service

# The six named clinical scenarios (Section 5) — three already existed in
# Forge's TEMPLATE_CATEGORIES (loaner_instrument, vendor_tray,
# robotic_instrument); three were added for Athena.
CLINICAL_PLAYBOOK_CATEGORIES = [
    "blood_detection_investigation", "corrosion_investigation", "loaner_instrument",
    "joint_commission_preparation", "vendor_tray", "robotic_instrument",
]


class PlaybookNotFoundError(ValueError):
    pass


def create_playbook(
    db: Session, tenant_id: str, *, name: str, category: str, description: str = "",
    nodes: list[dict], edges: list[dict], author: str, linked_standards: list[str] | None = None,
) -> dict:
    if category not in CLINICAL_PLAYBOOK_CATEGORIES:
        raise ValueError(f"category must be one of {CLINICAL_PLAYBOOK_CATEGORIES}")
    created = forge_workflow_service.create_workflow(
        db, tenant_id, name=name, description=description, category=category, nodes=nodes, edges=edges, author=author,
    )
    row = forge_workflow_service.get_workflow_row_or_404(db, created["id"])
    row.is_template = True
    row.linked_standards_json = json.dumps(linked_standards or [])
    db.commit()
    db.refresh(row)
    return forge_workflow_service.get_workflow(db, row.id)


def list_playbooks(db: Session, tenant_id: str, *, category: str = "") -> list[dict]:
    q = db.query(WorkflowDefinition).filter(
        (WorkflowDefinition.tenant_id == tenant_id) | (WorkflowDefinition.tenant_id == ""),
        WorkflowDefinition.is_template.is_(True),
        WorkflowDefinition.category.in_(CLINICAL_PLAYBOOK_CATEGORIES),
        WorkflowDefinition.is_current.is_(True),
    )
    if category:
        q = q.filter(WorkflowDefinition.category == category)
    return [forge_workflow_service.workflow_row_to_dict(r) for r in q.order_by(WorkflowDefinition.id.desc()).all()]


def get_playbook(db: Session, workflow_id: int) -> dict:
    result = forge_workflow_service.get_workflow(db, workflow_id)
    if result is None:
        raise PlaybookNotFoundError(f"Playbook {workflow_id} not found.")
    return result


def attach_standard(db: Session, workflow_id: int, standard_code: str) -> dict:
    row = forge_workflow_service.get_workflow_row_or_404(db, workflow_id)
    standards = json.loads(row.linked_standards_json or "[]")
    if standard_code not in standards:
        standards.append(standard_code)
    row.linked_standards_json = json.dumps(standards)
    db.commit()
    db.refresh(row)
    return forge_workflow_service.workflow_row_to_dict(row)


def playbook_version_history(db: Session, workflow_id: int) -> list[dict]:
    return forge_workflow_service.version_history(db, workflow_id)
