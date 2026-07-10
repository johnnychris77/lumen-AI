"""v4.1 — Project Forge, Section 4: Workflow Templates.

Nine named starter templates, seeded as global (`tenant_id == ""`)
`WorkflowDefinition` rows with `is_template=True`, `status=published` —
reusing the exact same model Section 1's Workflow Designer uses, not a
second template table. Each template's node graph is a real, minimal,
valid Start→...→End chain using only node types from
`app.models.workflow_forge.NODE_TYPES` — nothing fabricated.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.workflow_forge import STATUS_PUBLISHED, TEMPLATE_CATEGORIES, WorkflowDefinition


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

_TEMPLATE_NAMES = {
    "general_instrument_inspection": "General Instrument Inspection",
    "rigid_scope": "Rigid Scope Workflow",
    "flexible_endoscope": "Flexible Endoscope Workflow",
    "loaner_instrument": "Loaner Instrument Workflow",
    "vendor_tray": "Vendor Tray Workflow",
    "robotic_instrument": "Robotic Instrument Workflow",
    "orthopedic": "Orthopedic Workflow",
    "neurosurgery": "Neurosurgery Workflow",
    "custom_organization": "Custom Organization Workflow",
}


def _default_graph(category: str) -> tuple[list[dict], list[dict]]:
    """A minimal, valid Start -> Inspection -> AI Analysis -> Supervisor
    Review -> End chain — the same shape for every template, since the
    sprint's own examples describe this as the common baseline shape;
    organizations customize from here rather than starting from nothing."""
    nodes = [
        {"key": "start", "type": "start", "label": "Start", "x": 0, "y": 0},
        {"key": "inspection", "type": "inspection", "label": "Inspection", "x": 200, "y": 0},
        {"key": "ai_analysis", "type": "ai_analysis", "label": "AI Analysis", "x": 400, "y": 0},
        {"key": "supervisor_review", "type": "supervisor_review", "label": "Supervisor Review", "x": 600, "y": 0},
        {"key": "end", "type": "end", "label": "End", "x": 800, "y": 0},
    ]
    edges = [
        {"from": "start", "to": "inspection"},
        {"from": "inspection", "to": "ai_analysis"},
        {"from": "ai_analysis", "to": "supervisor_review"},
        {"from": "supervisor_review", "to": "end"},
    ]
    return nodes, edges


def _seed_templates(db: Session) -> None:
    for category in TEMPLATE_CATEGORIES:
        existing = db.query(WorkflowDefinition).filter(
            WorkflowDefinition.tenant_id == "", WorkflowDefinition.is_template.is_(True),
            WorkflowDefinition.category == category,
        ).first()
        if existing is not None:
            continue
        nodes, edges = _default_graph(category)
        db.add(WorkflowDefinition(
            tenant_id="", workflow_ref=_new_ref(), name=_TEMPLATE_NAMES[category],
            description=f"Starter template for {_TEMPLATE_NAMES[category]}.", category=category,
            nodes_json=json.dumps(nodes), edges_json=json.dumps(edges), version=1,
            status=STATUS_PUBLISHED, is_current=True, author="system", is_template=True,
        ))
    db.commit()


def list_templates(db: Session) -> list[dict]:
    _seed_templates(db)
    rows = db.query(WorkflowDefinition).filter(
        WorkflowDefinition.tenant_id == "", WorkflowDefinition.is_template.is_(True),
    ).order_by(WorkflowDefinition.category.asc()).all()
    return [_row_to_dict(r) for r in rows]


def get_template(db: Session, category: str) -> dict | None:
    _seed_templates(db)
    row = db.query(WorkflowDefinition).filter(
        WorkflowDefinition.tenant_id == "", WorkflowDefinition.is_template.is_(True),
        WorkflowDefinition.category == category,
    ).first()
    return _row_to_dict(row) if row else None
