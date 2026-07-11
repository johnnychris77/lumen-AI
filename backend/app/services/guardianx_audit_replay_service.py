"""v5.2 — Project GuardianX, Section 4: Audit Replay.

No new table -- a replay composes what already exists:

  * `Inspection` (the source record) and `WorkflowExecution`'s
    already-captured `decision_path_json`/`execution_log_json`
    (Forge, v4.1) for the exact nodes visited and the timeline
    (`started_at`/`completed_at`).
  * The linked `WorkflowDefinition`/`WorkflowRule` rows, at the exact
    version referenced (Forge's `is_current`/`version` pattern), for
    "Model version, Rules".
  * `GuardianX`'s own `EvidenceLedgerEntry`/`AIExplainabilityRecord`
    rows for "Knowledge, Evidence".
  * `audit_chain_verification_service.verify_audit_chain` for a real,
    tamper-evident timeline of every recorded action against the
    resource -- never a fabricated "audit trail".
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.workflow_forge import WorkflowDefinition, WorkflowExecution, WorkflowRule
from app.services import guardianx_evidence_ledger_service, guardianx_explainability_service
from app.services.audit_chain_verification_service import verify_audit_chain


class ReplayNotFoundError(Exception):
    pass


def replay_inspection(db: Session, inspection_id: int) -> dict:
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if inspection is None:
        raise ReplayNotFoundError(f"Inspection {inspection_id} not found.")

    return {
        "inspection_id": inspection.id,
        "timeline": {"created_at": inspection.created_at.isoformat()},
        "stain_detected": inspection.stain_detected,
        "confidence": inspection.confidence,
        "evidence_ledger": guardianx_evidence_ledger_service.list_entries_for_source(db, "inspection", str(inspection_id)),
        "explanations": guardianx_explainability_service.list_explanations_for_source(db, "inspection", str(inspection_id)),
        "audit_chain": verify_audit_chain(db, resource_type="inspection", resource_id=str(inspection_id)),
    }


def replay_workflow_execution(db: Session, execution_id: int) -> dict:
    execution = db.query(WorkflowExecution).filter(WorkflowExecution.id == execution_id).first()
    if execution is None:
        raise ReplayNotFoundError(f"Workflow execution {execution_id} not found.")

    workflow = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == execution.workflow_id).first()
    decision_path = json.loads(execution.decision_path_json or "[]")
    execution_log = json.loads(execution.execution_log_json or "[]")

    return {
        "execution_id": execution.id,
        "model_version": {"workflow_id": workflow.id, "version": workflow.version, "name": workflow.name} if workflow else None,
        "decision_path": decision_path,
        "execution_log": execution_log,
        "timeline": {
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "execution_time_ms": execution.execution_time_ms,
        },
        "evidence_ledger": guardianx_evidence_ledger_service.list_entries_for_source(db, "workflow_execution", str(execution_id)),
        "audit_chain": verify_audit_chain(db, resource_type="workflow_execution", resource_id=str(execution_id)),
    }


def replay_rule(db: Session, rule_id: int) -> dict:
    rule = db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()
    if rule is None:
        raise ReplayNotFoundError(f"Workflow rule {rule_id} not found.")
    return {
        "rule_id": rule.id, "name": rule.name, "version": rule.version,
        "condition": json.loads(rule.condition_json or "{}"),
        "actions": json.loads(rule.actions_json or "[]"),
        "approval_status": rule.approval_status,
    }


def replay_recommendation(db: Session, source_type: str, source_id: str) -> dict:
    """Generic replay for any AI recommendation, keyed the same way
    `EvidenceLedgerEntry`/`AIExplainabilityRecord` are: by `source_type`/
    `source_id` reference, never a copy of the underlying content."""
    return {
        "source_type": source_type,
        "source_id": source_id,
        "evidence_ledger": guardianx_evidence_ledger_service.list_entries_for_source(db, source_type, source_id),
        "explanations": guardianx_explainability_service.list_explanations_for_source(db, source_type, source_id),
        "audit_chain": verify_audit_chain(db, resource_type=source_type, resource_id=source_id),
    }
