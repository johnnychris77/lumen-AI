"""v5.4 — LumenAI Network: Project Nova — Autonomous AI Agent Platform
routes.

Frontend route: /agents. API prefix: /api/nova.

**A real, working multi-agent pipeline already exists** at `/api/agents/*`
(`app/agents/*.py`, "Phase 22") -- this router never duplicates it; see
`app/models/nova_agent_platform.py` for the full naming disambiguation.

Uses `tenant_authz.require_tenant_roles` (real `TenantMembership`
verification), consistent with Athena/Phoenix/Infinity/Olympus/
GuardianX/Genesis AI.

  * POST  /agents/seed-core, GET /agents, GET /agents/{key},
    PATCH  /agents/{key}/status, POST /agents/{key}/invoke            — Sections 1, 2, 4
  * GET   /messages                                                    — Section 3
  * POST  /task-runs, POST /task-runs/{id}/advance,
    POST  /task-runs/{id}/fail, GET /task-runs/{id}, GET /task-runs    — Section 5
  * POST  /agents/{key}/memory, GET /agents/{key}/memory               — Section 6
  * POST  /collaboration-requests, POST /collaboration-requests/{id}/resolve,
    GET   /collaboration-requests/{id}, GET /collaboration-requests    — Section 7
  * GET   /marketplace/summary                                         — Section 8
  * GET   /observability/summary                                       — Section 9
  * GET   /summary                                                     — umbrella
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services import (
    nova_agent_registry_service,
    nova_collaboration_service,
    nova_communication_bus_service,
    nova_core_agent_invocation_service,
    nova_marketplace_service,
    nova_memory_service,
    nova_observability_service,
    nova_orchestration_service,
    nova_platform_summary_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/nova", tags=["nova"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


# ---------------------------------------------------------------------------
# Sections 1, 2, 4 — Agent Framework, Registry, Core Agents
# ---------------------------------------------------------------------------


@router.post("/agents/seed-core")
def post_seed_core_agents(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    return {"agents": nova_agent_registry_service.seed_core_agents(db, registered_by=actor)}


@router.get("/agents")
def get_agents(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return nova_agent_registry_service.list_all_agents(db)


@router.get("/agents/{agent_key}")
def get_agent(agent_key: str, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return nova_agent_registry_service.get_agent(db, agent_key)
    except nova_agent_registry_service.UnknownAgentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/agents/{agent_key}/status")
def patch_agent_status(agent_key: str, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return nova_agent_registry_service.set_agent_status(db, agent_key, status=payload.get("status", ""))
    except nova_agent_registry_service.UnknownAgentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/agents/{agent_key}/invoke")
def post_invoke_agent(agent_key: str, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    try:
        return nova_core_agent_invocation_service.invoke_agent(db, agent_key, tenant_id, kwargs=payload.get("kwargs", {}))
    except nova_core_agent_invocation_service.UnknownAgentInvocationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 3 — Agent Communication Bus
# ---------------------------------------------------------------------------


@router.get("/messages")
def get_messages(
    agent_key: str = Query(""), limit: int = Query(100, le=500),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"messages": nova_communication_bus_service.list_messages(db, _tenant(current_user), agent_key=agent_key, limit=limit)}


# ---------------------------------------------------------------------------
# Section 5 — Task Orchestration
# ---------------------------------------------------------------------------


@router.post("/task-runs", status_code=201)
def post_task_run(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        return nova_orchestration_service.start_task_run(
            db, tenant_id, pipeline_name=payload.get("pipeline_name", ""), agent_sequence=payload.get("agent_sequence", []),
            triggered_by=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/task-runs/{task_run_id}/advance")
def post_task_run_advance(task_run_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return nova_orchestration_service.advance_step(db, task_run_id, output_summary=payload.get("output_summary"))
    except nova_orchestration_service.UnknownTaskRunError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except nova_orchestration_service.TaskRunNotRunningError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/task-runs/{task_run_id}/fail")
def post_task_run_fail(task_run_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return nova_orchestration_service.fail_task_run(db, task_run_id, reason=payload.get("reason", ""))
    except nova_orchestration_service.UnknownTaskRunError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/task-runs/{task_run_id}")
def get_task_run(task_run_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return nova_orchestration_service.get_task_run(db, task_run_id)
    except nova_orchestration_service.UnknownTaskRunError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/task-runs")
def get_task_runs(
    status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"task_runs": nova_orchestration_service.list_task_runs(db, _tenant(current_user), status=status)}


# ---------------------------------------------------------------------------
# Section 6 — Agent Memory
# ---------------------------------------------------------------------------


@router.post("/agents/{agent_key}/memory", status_code=201)
def post_agent_memory(agent_key: str, payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    try:
        return nova_memory_service.record_memory(
            db, agent_key, tenant_id, memory_type=payload.get("memory_type", ""), content=payload.get("content", {}),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/agents/{agent_key}/memory")
def get_agent_memory(
    agent_key: str, memory_type: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    tenant_id = _tenant(current_user)
    try:
        return {"memory": nova_memory_service.list_memory(db, agent_key, tenant_id, memory_type=memory_type)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 7 — Human-Agent Collaboration
# ---------------------------------------------------------------------------


@router.post("/collaboration-requests", status_code=201)
def post_collaboration_request(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        return nova_collaboration_service.create_request(
            db, payload.get("agent_key", ""), tenant_id, request_type=payload.get("request_type", ""),
            description=payload.get("description", ""), requested_by=actor, task_run_id=payload.get("task_run_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/collaboration-requests/{request_id}/resolve")
def post_collaboration_request_resolve(request_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    actor = _actor(current_user)
    try:
        return nova_collaboration_service.resolve_request(
            db, request_id, decision=payload.get("decision", ""), resolution=payload.get("resolution", ""), resolved_by=actor,
        )
    except nova_collaboration_service.UnknownCollaborationRequestError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, nova_collaboration_service.InvalidCollaborationStateError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/collaboration-requests/{request_id}")
def get_collaboration_request(request_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return nova_collaboration_service.get_request(db, request_id)
    except nova_collaboration_service.UnknownCollaborationRequestError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/collaboration-requests")
def get_collaboration_requests(
    agent_key: str = Query(""), status: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"requests": nova_collaboration_service.list_requests(db, _tenant(current_user), agent_key=agent_key, status=status)}


# ---------------------------------------------------------------------------
# Section 8 — Agent Marketplace
# ---------------------------------------------------------------------------


@router.get("/marketplace/summary")
def get_marketplace_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return nova_marketplace_service.agent_marketplace_summary(db)


# ---------------------------------------------------------------------------
# Section 9 — Observability
# ---------------------------------------------------------------------------


@router.get("/observability/summary")
def get_observability_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return nova_observability_service.observability_summary(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Umbrella
# ---------------------------------------------------------------------------


@router.get("/summary")
def get_platform_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return nova_platform_summary_service.platform_summary(db, _tenant(current_user))
