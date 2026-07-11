"""v5.4 — Project Nova, Section 5: Task Orchestration.

`AgentTaskRun` is a configurable ordered pipeline of `agent_key`s,
distinct from Phase 22's hardcoded 10-step inspection pipeline (which
keeps its own `run_pipeline` entry point unchanged, reachable at
`/api/agents/run/{inspection_id}`). Every step advance is logged to the
Communication Bus (`nova_communication_bus_service.py`), so a task run's
full reasoning trail is always reconstructable.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.nova_agent_platform import TASK_RUN_COMPLETED, TASK_RUN_FAILED, TASK_RUN_RUNNING, AgentTaskRun
from app.services import nova_communication_bus_service


class UnknownTaskRunError(Exception):
    pass


class TaskRunNotRunningError(Exception):
    pass


def _to_dict(row: AgentTaskRun) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "pipeline_name": row.pipeline_name,
        "agent_sequence": json.loads(row.agent_sequence_json or "[]"),
        "status": row.status,
        "current_step_index": row.current_step_index,
        "step_log": json.loads(row.step_log_json or "[]"),
        "triggered_by": row.triggered_by,
        "human_review_required": row.human_review_required,
        "started_at": row.started_at.isoformat(),
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def start_task_run(db: Session, tenant_id: str, *, pipeline_name: str, agent_sequence: list[str], triggered_by: str) -> dict:
    if not agent_sequence:
        raise ValueError("agent_sequence must not be empty.")
    row = AgentTaskRun(
        tenant_id=tenant_id, pipeline_name=pipeline_name, agent_sequence_json=json.dumps(agent_sequence),
        triggered_by=triggered_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get_or_404(db: Session, task_run_id: int) -> AgentTaskRun:
    row = db.query(AgentTaskRun).filter(AgentTaskRun.id == task_run_id).first()
    if row is None:
        raise UnknownTaskRunError(f"Agent task run {task_run_id} not found.")
    return row


def advance_step(db: Session, task_run_id: int, *, output_summary: dict | None = None) -> dict:
    row = _get_or_404(db, task_run_id)
    if row.status != TASK_RUN_RUNNING:
        raise TaskRunNotRunningError(f"Task run {task_run_id} is '{row.status}', not running.")

    sequence = json.loads(row.agent_sequence_json or "[]")
    if row.current_step_index >= len(sequence):
        raise TaskRunNotRunningError(f"Task run {task_run_id} has no remaining steps.")

    current_agent = sequence[row.current_step_index]
    next_index = row.current_step_index + 1
    next_agent = sequence[next_index] if next_index < len(sequence) else "supervisor_agent"

    nova_communication_bus_service.log_message(
        db, row.tenant_id, source_agent_key=current_agent, target_agent_key=next_agent,
        payload=output_summary or {}, task_run_id=row.id,
    )

    step_log = json.loads(row.step_log_json or "[]")
    step_log.append({"agent_key": current_agent, "output_summary": output_summary or {}})
    row.step_log_json = json.dumps(step_log)
    row.current_step_index = next_index
    if row.current_step_index >= len(sequence):
        row.status = TASK_RUN_COMPLETED
        row.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def fail_task_run(db: Session, task_run_id: int, *, reason: str) -> dict:
    row = _get_or_404(db, task_run_id)
    row.status = TASK_RUN_FAILED
    row.completed_at = datetime.now(timezone.utc)
    step_log = json.loads(row.step_log_json or "[]")
    step_log.append({"failure_reason": reason})
    row.step_log_json = json.dumps(step_log)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def get_task_run(db: Session, task_run_id: int) -> dict:
    return _to_dict(_get_or_404(db, task_run_id))


def list_task_runs(db: Session, tenant_id: str, *, status: str = "") -> list[dict]:
    query = db.query(AgentTaskRun).filter(AgentTaskRun.tenant_id == tenant_id)
    if status:
        query = query.filter(AgentTaskRun.status == status)
    rows = query.order_by(AgentTaskRun.started_at.desc()).all()
    return [_to_dict(r) for r in rows]
