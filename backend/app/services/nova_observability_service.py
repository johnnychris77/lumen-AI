"""v5.4 — Project Nova, Section 9: Observability.

Zero new tables. Every metric here is computed live from real rows --
`AgentDefinition.health`/`status`, `AgentMessage` counts, `AgentTaskRun`
outcomes. There is no latency instrumentation or resource-usage
telemetry anywhere in this codebase, so "Latency"/"Resource Usage" are
reported honestly as unavailable rather than fabricated, the same
discipline Phase 22's own registry established ("not a fabricated
uptime/latency metric").
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.nova_agent_platform import TASK_RUN_COMPLETED, TASK_RUN_FAILED, TASK_RUN_RUNNING, AgentDefinition, AgentMessage, AgentTaskRun


def agent_health_overview(db: Session) -> dict:
    rows = db.query(AgentDefinition).all()
    degraded = [r.agent_key for r in rows if r.health != "ok"]
    return {"agent_count": len(rows), "overall_status": "ok" if not degraded else "degraded", "degraded_agents": degraded}


def communication_volume(db: Session, tenant_id: str) -> dict:
    total = db.query(AgentMessage).filter(AgentMessage.tenant_id == tenant_id).count()
    return {"tenant_id": tenant_id, "total_messages": total}


def task_run_outcomes(db: Session, tenant_id: str) -> dict:
    rows = db.query(AgentTaskRun).filter(AgentTaskRun.tenant_id == tenant_id).all()
    return {
        "total_task_runs": len(rows),
        "running": sum(1 for r in rows if r.status == TASK_RUN_RUNNING),
        "completed": sum(1 for r in rows if r.status == TASK_RUN_COMPLETED),
        "failed": sum(1 for r in rows if r.status == TASK_RUN_FAILED),
    }


def observability_summary(db: Session, tenant_id: str) -> dict:
    return {
        "agent_health": agent_health_overview(db),
        "communication_volume": communication_volume(db, tenant_id),
        "task_run_outcomes": task_run_outcomes(db, tenant_id),
        "latency": {"available": False, "note": "No latency instrumentation exists in this codebase for these in-process agents."},
        "resource_usage": {"available": False, "note": "No resource-usage telemetry exists in this codebase."},
        "retries": {"available": False, "note": "No retry mechanism exists for agent task runs -- a failed run stays failed."},
    }
