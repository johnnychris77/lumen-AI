"""v5.4 — Project Nova, Section 3: Agent Communication Bus.

"Every interaction is logged." `AgentMessage` is genuinely new. Phase
22's `run_pipeline` already builds an in-memory `trace` list per real
inspection run but never persists it -- `log_pipeline_trace` is a thin
adapter that persists those *real* trace entries as `AgentMessage` rows,
never a re-derivation of the pipeline's own reasoning.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.nova_agent_platform import AgentMessage


def _to_dict(row: AgentMessage) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "source_agent_key": row.source_agent_key,
        "target_agent_key": row.target_agent_key,
        "task_run_id": row.task_run_id,
        "payload": json.loads(row.payload_json or "{}"),
        "logged_at": row.logged_at.isoformat(),
    }


def log_message(
    db: Session, tenant_id: str, *, source_agent_key: str, target_agent_key: str,
    payload: dict | None = None, task_run_id: int | None = None,
) -> dict:
    row = AgentMessage(
        tenant_id=tenant_id, source_agent_key=source_agent_key, target_agent_key=target_agent_key,
        task_run_id=task_run_id, payload_json=json.dumps(payload or {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def log_pipeline_trace(db: Session, tenant_id: str, trace: list[dict]) -> list[dict]:
    """Persists Phase 22's real `run_pipeline` trace as a chain of
    `AgentMessage` rows -- each step logged as (previous agent -> this
    agent), so the communication bus reflects the exact pipeline order
    Section 3 names (Inspection -> Knowledge -> Digital Twin ->
    Recommendation -> Supervisor)."""
    logged = []
    previous_agent = "inspection_agent"
    for entry in trace:
        row = log_message(
            db, tenant_id, source_agent_key=previous_agent, target_agent_key=entry["agent"],
            payload={"version": entry["version"], "output_summary": entry["output_summary"]},
        )
        logged.append(row)
        previous_agent = entry["agent"]
    return logged


def list_messages(db: Session, tenant_id: str, *, agent_key: str = "", limit: int = 100) -> list[dict]:
    query = db.query(AgentMessage).filter(AgentMessage.tenant_id == tenant_id)
    if agent_key:
        query = query.filter(
            (AgentMessage.source_agent_key == agent_key) | (AgentMessage.target_agent_key == agent_key)
        )
    rows = query.order_by(AgentMessage.logged_at.desc()).limit(limit).all()
    return [_to_dict(r) for r in rows]
