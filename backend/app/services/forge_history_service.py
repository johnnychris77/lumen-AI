"""v4.1 — Project Forge, Section 11: /workflow-history.

Composes `forge_workflow_service.version_history` (Section 9) and
`forge_execution_service.list_executions` (Sections 1 & 8) into one
history view per workflow — a presentation layer, not a third
history-of-record table.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import forge_execution_service, forge_workflow_service


def workflow_history(db: Session, tenant_id: str, workflow_id: int) -> dict:
    return {
        "versions": forge_workflow_service.version_history(db, workflow_id),
        "executions": forge_execution_service.list_executions(db, tenant_id, workflow_id=workflow_id, is_simulation=False),
        "simulations": forge_execution_service.list_executions(db, tenant_id, workflow_id=workflow_id, is_simulation=True),
    }
