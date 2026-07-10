"""v4.1 — LumenAI OS: Project Forge — AI Workflow Builder & No-Code
Clinical Rules Engine routes.

Frontend route: /workflow-builder.
API prefix: /api/forge.

  * POST/GET /workflows, GET /workflows/{id}, POST /workflows/{id}/revise|
    publish|archive|rollback, GET /workflows/{id}/versions          — Sections 1, 9
  * POST/GET /workflow-rules, GET /workflow-rules/{id},
    POST /workflow-rules/{id}/approve|evaluate                       — Sections 2, 3
  * GET /workflow-templates, GET /workflow-templates/{category}       — Section 4
  * POST /workflow-execution, POST /workflow-execution/simulate,
    GET /workflow-execution, GET /workflow-execution/{id}             — Sections 1 (exec), 8, 11
  * GET /workflow-history/{workflow_id}                               — Section 11
  * POST/GET /approval-chains, POST /approval-instances/{id}/decide,
    GET /approval-instances/{id}                                      — Section 7
  * GET /marketplace, POST /workflows/{id}/share,
    POST /workflows/{id}/approve-share, POST /workflows/{id}/clone,
    POST /workflow-templates/{category}/import,
    GET /workflows/{id}/export                                       — Section 10
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.services import (
    forge_approval_service,
    forge_execution_service,
    forge_history_service,
    forge_marketplace_service,
    forge_rule_engine,
    forge_simulation_service,
    forge_template_service,
    forge_workflow_service,
)
from app.services.forge_execution_service import UnknownWorkflowForExecutionError
from app.services.forge_marketplace_service import NotShareableError
from app.services.forge_rule_engine import InvalidConditionError, UnknownRuleError
from app.services.forge_workflow_service import InvalidWorkflowStateError, UnknownWorkflowError

router = APIRouter(prefix="/api/forge", tags=["forge"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")
_ADMIN_ROLES = ("admin",)


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


def _audit(db: Session, tenant_id: str, actor: str, action_type: str, resource_type: str, resource_id: str, details: dict) -> None:
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=actor, actor_role="",
        action_type=action_type, resource_type=resource_type, resource_id=resource_id, details=details, compliance_flag=True,
    )


# ---------------------------------------------------------------------------
# Sections 1 & 9 — Workflows
# ---------------------------------------------------------------------------


@router.post("/workflows")
def post_create_workflow(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = forge_workflow_service.create_workflow(
            db, tenant_id, name=payload["name"], description=payload.get("description", ""),
            category=payload.get("category", ""), nodes=payload.get("nodes", []), edges=payload.get("edges", []),
            author=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, _actor(current_user), "forge.workflow_created", "forge_workflow_definitions", str(result["id"]), {"name": payload["name"]})
    return result


@router.get("/workflows")
def get_workflows(
    request: Request, category: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"workflows": forge_workflow_service.list_workflows(db, tenant_id, category=category)}


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    result = forge_workflow_service.get_workflow(db, workflow_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found.")
    return result


@router.post("/workflows/{workflow_id}/revise")
def post_revise_workflow(
    workflow_id: int, payload: dict, current_user=Depends(require_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        return forge_workflow_service.revise_workflow(
            db, workflow_id, updated_by=_actor(current_user), nodes=payload.get("nodes"), edges=payload.get("edges"),
            name=payload.get("name"), description=payload.get("description"),
        )
    except UnknownWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/workflows/{workflow_id}/publish")
def post_publish_workflow(workflow_id: int, current_user=Depends(require_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return forge_workflow_service.publish_workflow(db, workflow_id, approved_by=_actor(current_user))
    except UnknownWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidWorkflowStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/workflows/{workflow_id}/archive")
def post_archive_workflow(workflow_id: int, current_user=Depends(require_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return forge_workflow_service.archive_workflow(db, workflow_id)
    except UnknownWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/workflows/{workflow_id}/versions")
def get_workflow_versions(workflow_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"versions": forge_workflow_service.version_history(db, workflow_id)}


@router.post("/workflows/{workflow_id}/rollback")
def post_rollback_workflow(
    workflow_id: int, payload: dict, current_user=Depends(require_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        return forge_workflow_service.rollback_to_version(
            db, workflow_id, payload["target_version_id"], rolled_back_by=_actor(current_user),
        )
    except UnknownWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidWorkflowStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Sections 2 & 3 — Clinical Rule Engine + No-Code Rule Builder
# ---------------------------------------------------------------------------


@router.post("/workflow-rules")
def post_create_rule(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = forge_rule_engine.create_rule(
            db, tenant_id, name=payload["name"], description=payload.get("description", ""),
            condition=payload["condition"], actions=payload.get("actions", []), author=_actor(current_user),
        )
    except InvalidConditionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, _actor(current_user), "forge.rule_created", "forge_workflow_rules", str(result["id"]), {"name": payload["name"]})
    return result


@router.get("/workflow-rules")
def get_rules(
    request: Request, approval_status: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"rules": forge_rule_engine.list_rules(db, tenant_id, approval_status=approval_status)}


@router.get("/workflow-rules/{rule_id}")
def get_rule(rule_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    result = forge_rule_engine.get_rule(db, rule_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found.")
    return result


@router.post("/workflow-rules/{rule_id}/approve")
def post_approve_rule(rule_id: int, current_user=Depends(require_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return forge_rule_engine.approve_rule(db, rule_id, approved_by=_actor(current_user))
    except UnknownRuleError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/workflow-rules/{rule_id}/evaluate")
def post_evaluate_rule(rule_id: int, payload: dict, current_user=Depends(require_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return forge_rule_engine.evaluate_rule(db, rule_id, payload.get("context", {}))
    except UnknownRuleError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 4 — Workflow Templates
# ---------------------------------------------------------------------------


@router.get("/workflow-templates")
def get_templates(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"templates": forge_template_service.list_templates(db)}


@router.get("/workflow-templates/{category}")
def get_template(category: str, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    result = forge_template_service.get_template(db, category)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Template '{category}' not found.")
    return result


@router.post("/workflow-templates/{category}/import")
def post_import_template(
    category: str, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return forge_marketplace_service.import_template(db, tenant_id, category, imported_by=_actor(current_user))
    except UnknownWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Sections 1 (execution), 8 (simulation) & 11 (/workflow-execution)
# ---------------------------------------------------------------------------


@router.post("/workflow-execution")
def post_execute_workflow(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = forge_execution_service.execute_workflow(
            db, tenant_id, payload["workflow_id"], inspection_id=payload.get("inspection_id"),
            triggered_by=_actor(current_user),
        )
    except UnknownWorkflowForExecutionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit(db, tenant_id, _actor(current_user), "forge.workflow_executed", "forge_workflow_executions", str(result["id"]), {"workflow_id": payload["workflow_id"]})
    return result


@router.post("/workflow-execution/simulate")
def post_simulate_workflow(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return forge_simulation_service.simulate_workflow(
            db, tenant_id, payload["workflow_id"], payload["inspection_id"], triggered_by=_actor(current_user),
            expected_outcome=payload.get("expected_outcome", ""),
        )
    except UnknownWorkflowForExecutionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/workflow-execution")
def get_executions(
    request: Request, workflow_id: int | None = Query(None), is_simulation: bool | None = Query(None),
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"executions": forge_execution_service.list_executions(db, tenant_id, workflow_id=workflow_id, is_simulation=is_simulation)}


@router.get("/workflow-execution/{execution_id}")
def get_execution(execution_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    result = forge_execution_service.get_execution(db, execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 11 — /workflow-history
# ---------------------------------------------------------------------------


@router.get("/workflow-history/{workflow_id}")
def get_workflow_history(
    workflow_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return forge_history_service.workflow_history(db, tenant_id, workflow_id)


# ---------------------------------------------------------------------------
# Section 7 — Approval Workflows
# ---------------------------------------------------------------------------


@router.post("/approval-chains")
def post_create_chain(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return forge_approval_service.create_chain(db, tenant_id, name=payload["name"], steps=payload.get("steps"))


@router.get("/approval-chains")
def get_chains(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"chains": forge_approval_service.list_chains(db, tenant_id)}


@router.get("/approval-instances/{instance_id}")
def get_instance(instance_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    result = forge_approval_service.get_instance(db, instance_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Approval instance {instance_id} not found.")
    return result


@router.post("/approval-instances/{instance_id}/decide")
def post_decide_instance(
    instance_id: int, payload: dict, current_user=Depends(require_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    try:
        return forge_approval_service.decide_step(
            db, instance_id, decided_by=_actor(current_user), decided_role=payload.get("decided_role", getattr(current_user, "role", "")),
            decision=payload["decision"], notes=payload.get("notes", ""),
        )
    except forge_approval_service.UnknownApprovalInstanceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except forge_approval_service.ApprovalAlreadyDecidedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 10 — Forge Marketplace
# ---------------------------------------------------------------------------


@router.get("/marketplace")
def get_marketplace(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"listings": forge_marketplace_service.list_marketplace(db)}


@router.post("/workflows/{workflow_id}/clone")
def post_clone_workflow(
    workflow_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return forge_marketplace_service.clone_workflow(db, tenant_id, workflow_id, cloned_by=_actor(current_user), new_name=payload.get("new_name"))
    except UnknownWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/workflows/{workflow_id}/share")
def post_share_workflow(workflow_id: int, current_user=Depends(require_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return forge_marketplace_service.share_workflow(db, workflow_id, shared_by=_actor(current_user))
    except UnknownWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotShareableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/workflows/{workflow_id}/approve-share", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def post_approve_share(workflow_id: int, current_user=Depends(require_roles(*_ADMIN_ROLES)), db: Session = Depends(get_db)):
    try:
        result = forge_marketplace_service.approve_share(db, workflow_id, approved_by=_actor(current_user))
    except UnknownWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotShareableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _audit(db, "", _actor(current_user), "forge.marketplace_approved", "forge_workflow_definitions", str(workflow_id), {})
    return result


@router.get("/workflows/{workflow_id}/export")
def get_export_workflow(workflow_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    try:
        return forge_marketplace_service.export_workflow(db, workflow_id)
    except UnknownWorkflowError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
