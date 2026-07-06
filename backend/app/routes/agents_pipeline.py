"""Phase 22 — Multi-Agent Clinical Intelligence Platform routes.

Distinct from the pre-existing single-purpose app/agent/spd_agent.py
(legacy, unrelated). This is the Phase 22 multi-agent pipeline: registry,
orchestrated run, and explainable trace for a real inspection.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_pipeline
from app.agents.registry import get_registry
from app.authz import require_roles
from app.db import models
from app.deps import get_db

router = APIRouter(prefix="/api/agents", tags=["multi-agent-pipeline"])

_READ_ROLES = ("admin", "spd_manager", "operator", "viewer")


@router.get("/registry")
def get_agent_registry(current_user=Depends(require_roles(*_READ_ROLES))):
    """Section 12 — Agent Registry: status, version, capabilities, dependencies, health."""
    return {"agents": get_registry()}


@router.get("/health")
def get_agents_health(current_user=Depends(require_roles(*_READ_ROLES))):
    registry = get_registry()
    degraded = [a["name"] for a in registry if a["health"] != "ok"]
    return {
        "overall_status": "ok" if not degraded else "degraded",
        "agent_count": len(registry),
        "degraded_agents": degraded,
    }


def _get_inspection(db: Session, inspection_id: int, tenant_id: str):
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return insp


@router.get("/run/{inspection_id}")
def run_agent_pipeline(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 13 — run the full agent pipeline for one real inspection."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    insp = _get_inspection(db, inspection_id, tenant_id)
    return run_pipeline(db, insp, tenant_id)


@router.get("/trace/{inspection_id}")
def get_agent_trace(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 14 — Explainable Agent Trace: which agent produced which decision."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    insp = _get_inspection(db, inspection_id, tenant_id)
    result = run_pipeline(db, insp, tenant_id)
    return {
        "inspection_id": inspection_id,
        "trace": result["trace"],
        "final_recommendation": result["recommendation_context"],
    }
