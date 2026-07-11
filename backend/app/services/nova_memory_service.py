"""v5.4 — Project Nova, Section 6: Agent Memory.

Every `AgentMemoryEntry` is tenant-aware and typed (working,
conversation context, historical learning, task history, evidence) --
"memory remains governed and tenant-aware": every query here is scoped
to a `tenant_id`, never a cross-tenant read.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.nova_agent_platform import MEMORY_TYPES, AgentMemoryEntry


def _to_dict(row: AgentMemoryEntry) -> dict:
    return {
        "id": row.id,
        "agent_key": row.agent_key,
        "tenant_id": row.tenant_id,
        "memory_type": row.memory_type,
        "content": json.loads(row.content_json or "{}"),
        "created_at": row.created_at.isoformat(),
    }


def record_memory(db: Session, agent_key: str, tenant_id: str, *, memory_type: str, content: dict) -> dict:
    if memory_type not in MEMORY_TYPES:
        raise ValueError(f"memory_type must be one of {MEMORY_TYPES}")
    row = AgentMemoryEntry(agent_key=agent_key, tenant_id=tenant_id, memory_type=memory_type, content_json=json.dumps(content))
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def list_memory(db: Session, agent_key: str, tenant_id: str, *, memory_type: str = "", limit: int = 50) -> list[dict]:
    query = db.query(AgentMemoryEntry).filter(AgentMemoryEntry.agent_key == agent_key, AgentMemoryEntry.tenant_id == tenant_id)
    if memory_type:
        if memory_type not in MEMORY_TYPES:
            raise ValueError(f"memory_type must be one of {MEMORY_TYPES}")
        query = query.filter(AgentMemoryEntry.memory_type == memory_type)
    rows = query.order_by(AgentMemoryEntry.created_at.desc()).limit(limit).all()
    return [_to_dict(r) for r in rows]
