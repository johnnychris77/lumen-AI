"""Project Steward: Governed Action Execution, Change Management &
Benefits Realization routes.

Frontend route: /steward. API prefix: /api/steward.

Uses `tenant_authz.require_tenant_roles` for tenant-scoped access (Section
27 -- cross-tenant action access is always denied, since every query
below filters by the authenticated user's own `tenant_id`). Finer-grained
authority-tier checks (approving/closing a high-risk action requires a
higher tier than a standard-risk one; a non-admin-tier approver is scope-
limited to their own facility) are enforced inside
`steward_action_service.transition_status`, mirroring Council's own
five-tier authority scale layered on the same four real RBAC roles.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.deps import get_db
from app.services import (
    steward_action_board_service,
    steward_action_service,
    steward_benefits_realization_service,
    steward_change_management_service,
    steward_closure_service,
    steward_council_integration_service,
    steward_escalation_service,
    steward_notification_service,
    steward_plan_generator_service,
    steward_reports_service,
    steward_residual_risk_service,
    steward_rollout_service,
    steward_timeline_service,
    steward_unintended_consequence_service,
    steward_verification_service,
    steward_workspace_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/steward", tags=["steward"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")
_MEDIA_TYPES = {"pdf": "application/pdf", "csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


def _role(current_user: dict) -> str:
    return current_user["role"] or "viewer"


def _parse_datetime_fields(payload: dict, *fields: str) -> dict:
    """JSON request bodies carry timestamps as ISO strings; the service
    layer expects real `datetime` objects."""
    parsed = dict(payload)
    for field in fields:
        value = parsed.get(field)
        if isinstance(value, str):
            parsed[field] = datetime.fromisoformat(value)
    return parsed


# ---------------------------------------------------------------------------
# Sections 1 & 2 — Governed Action CRUD
# ---------------------------------------------------------------------------


@router.post("/actions", status_code=201)
def post_create_action(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_action_service.create_action(
            db, _tenant(current_user), changed_by=_actor(current_user), changed_by_role=_role(current_user),
            **_parse_datetime_fields(payload, "approval_timestamp", "due_date"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_action_service.to_dict(row)


@router.post("/actions/from-council/{council_case_id}", status_code=201)
def post_create_action_from_council(
    council_case_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        row = steward_council_integration_service.create_action_from_council_decision(db, _tenant(current_user), council_case_id, **payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_action_service.to_dict(row)


@router.get("/actions")
def get_actions(
    status: str = Query(""), owner: str = Query(""), facility_id: str = Query(""), source_type: str = Query(""),
    risk_level: str = Query(""), category: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"actions": steward_action_service.list_actions(
        db, _tenant(current_user), status=status, owner=owner, facility_id=facility_id, source_type=source_type,
        risk_level=risk_level, category=category,
    )}


@router.get("/actions/{action_id}")
def get_action_detail(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    action = steward_action_service.get_action(db, tenant_id, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Governed Action not found")
    return {
        "action": steward_action_service.to_dict(action),
        "audit_history": steward_action_service.audit_history(db, tenant_id, action_id),
        "rollouts": steward_rollout_service.list_rollouts(db, tenant_id, action_id),
        "verifications": steward_verification_service.list_verifications(db, tenant_id, action_id),
        "outcome_reviews": steward_benefits_realization_service.list_outcome_reviews(db, tenant_id, action_id),
        "unintended_consequences": steward_unintended_consequence_service.list_consequences(db, tenant_id, action_id),
        "residual_risk_reviews": steward_residual_risk_service.list_residual_risk_reviews(db, tenant_id, action_id),
    }


@router.post("/actions/{action_id}/owner")
def post_assign_owner(action_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_action_service.assign_owner(
            db, _tenant(current_user), action_id, owner=payload.get("owner", ""), accountable_leader=payload.get("accountable_leader", ""),
            changed_by=_actor(current_user), changed_by_role=_role(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_action_service.to_dict(row)


@router.post("/actions/{action_id}/scope")
def post_update_scope(action_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_action_service.update_scope(
            db, _tenant(current_user), action_id, action_description=payload.get("action_description"),
            category=payload.get("category"), action_type=payload.get("action_type"),
            changed_by=_actor(current_user), changed_by_role=_role(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_action_service.to_dict(row)


@router.post("/actions/{action_id}/status")
def post_transition_status(action_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_action_service.transition_status(
            db, _tenant(current_user), action_id, new_status=payload["new_status"], changed_by=_actor(current_user),
            changed_by_role=_role(current_user), reason=payload.get("reason", ""),
            actor_facility_id=payload.get("actor_facility_id", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_action_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 4 — Implementation Plan Generator
# ---------------------------------------------------------------------------


@router.get("/actions/{action_id}/plan")
def get_plan(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return steward_plan_generator_service.generate_draft_plan(db, _tenant(current_user), action_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Sections 6 & 7 — Dependency Analysis and Change Management
# ---------------------------------------------------------------------------


@router.get("/actions/{action_id}/dependencies")
def get_dependencies(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return steward_change_management_service.analyze_dependencies(db, _tenant(current_user), action_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/actions/{action_id}/change-management")
def get_change_management(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return steward_change_management_service.generate_change_management_plan(db, _tenant(current_user), action_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/actions/{action_id}/change-readiness")
def post_change_readiness(action_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return steward_change_management_service.set_change_readiness(db, _tenant(current_user), action_id, change_readiness=payload["change_readiness"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 8 — Rollout Management
# ---------------------------------------------------------------------------


@router.post("/actions/{action_id}/rollouts", status_code=201)
def post_rollout(action_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_rollout_service.create_rollout(db, _tenant(current_user), action_id, **_parse_datetime_fields(payload, "start_date"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_rollout_service.to_dict(row)


@router.get("/actions/{action_id}/rollouts")
def get_rollouts(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"rollouts": steward_rollout_service.list_rollouts(db, _tenant(current_user), action_id)}


@router.post("/rollouts/{rollout_id}/result")
def post_rollout_result(rollout_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_rollout_service.record_rollout_result(db, _tenant(current_user), rollout_id, **payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return steward_rollout_service.to_dict(row)


@router.post("/rollouts/{rollout_id}/go-no-go")
def post_go_no_go(rollout_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_rollout_service.record_go_no_go(db, _tenant(current_user), rollout_id, decision=payload["decision"], rolled_back=payload.get("rolled_back", False))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_rollout_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 9 — Verification of Implementation
# ---------------------------------------------------------------------------


@router.post("/actions/{action_id}/verifications", status_code=201)
def post_verification(action_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_verification_service.record_verification(db, _tenant(current_user), action_id, **payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_verification_service.to_dict(row)


@router.get("/actions/{action_id}/verifications")
def get_verifications(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"verifications": steward_verification_service.list_verifications(db, _tenant(current_user), action_id)}


# ---------------------------------------------------------------------------
# Section 10 — Benefits Realization
# ---------------------------------------------------------------------------


@router.post("/actions/{action_id}/outcome-reviews", status_code=201)
def post_outcome_review(action_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_benefits_realization_service.record_outcome_review(db, _tenant(current_user), action_id, **payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_benefits_realization_service.to_dict(row)


@router.get("/actions/{action_id}/outcome-reviews")
def get_outcome_reviews(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"outcome_reviews": steward_benefits_realization_service.list_outcome_reviews(db, _tenant(current_user), action_id)}


# ---------------------------------------------------------------------------
# Section 11 — Unintended Consequence Monitoring
# ---------------------------------------------------------------------------


@router.post("/actions/{action_id}/unintended-consequences", status_code=201)
def post_unintended_consequence(action_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_unintended_consequence_service.flag_consequence(
            db, _tenant(current_user), action_id, changed_by=_actor(current_user), changed_by_role=_role(current_user), **payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_unintended_consequence_service.to_dict(row)


@router.get("/actions/{action_id}/unintended-consequences")
def get_unintended_consequences(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"unintended_consequences": steward_unintended_consequence_service.list_consequences(db, _tenant(current_user), action_id)}


@router.post("/unintended-consequences/{consequence_id}/review")
def post_review_consequence(consequence_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_unintended_consequence_service.review_consequence(db, _tenant(current_user), consequence_id, review_notes=payload.get("review_notes", ""))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return steward_unintended_consequence_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 20 — Residual Risk Review (Sentinel-X)
# ---------------------------------------------------------------------------


@router.post("/actions/{action_id}/residual-risk", status_code=201)
def post_residual_risk(action_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_residual_risk_service.record_residual_risk_review(db, _tenant(current_user), action_id, **payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_residual_risk_service.to_dict(row)


@router.get("/actions/{action_id}/residual-risk")
def get_residual_risk(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"residual_risk_reviews": steward_residual_risk_service.list_residual_risk_reviews(db, _tenant(current_user), action_id)}


# ---------------------------------------------------------------------------
# Section 24 — Closure Governance
# ---------------------------------------------------------------------------


@router.post("/actions/{action_id}/close")
def post_close_action(action_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = steward_closure_service.close_action(
            db, _tenant(current_user), action_id, closure_decision=payload["closure_decision"], closed_by=_actor(current_user),
            closed_by_role=_role(current_user), owner_comments=payload.get("owner_comments", ""),
            actor_facility_id=payload.get("actor_facility_id", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return steward_action_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 25 — Decision-to-Outcome Timeline
# ---------------------------------------------------------------------------


@router.get("/actions/{action_id}/timeline")
def get_timeline(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return steward_timeline_service.decision_to_outcome_timeline(db, _tenant(current_user), action_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 15 — Council integration
# ---------------------------------------------------------------------------


@router.get("/actions/{action_id}/council-status")
def get_council_status(action_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return steward_council_integration_service.council_status_return(db, _tenant(current_user), action_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 12 — Steward Workspace
# ---------------------------------------------------------------------------


@router.get("/workspace")
def get_workspace(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return steward_workspace_service.workspace_summary(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Section 14 — Leadership Action Boards
# ---------------------------------------------------------------------------


@router.get("/boards/supervisor")
def get_supervisor_board(facility_id: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return steward_action_board_service.supervisor_board(db, _tenant(current_user), facility_id=facility_id)


@router.get("/boards/manager")
def get_manager_board(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return steward_action_board_service.manager_board(db, _tenant(current_user))


@router.get("/boards/director")
def get_director_board(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return steward_action_board_service.director_board(db, _tenant(current_user))


@router.get("/boards/executive")
def get_executive_board(current_user: dict = Depends(require_tenant_roles("admin")), db: Session = Depends(get_db)):
    return steward_action_board_service.executive_board(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Section 22/23 — Notifications and Escalations
# ---------------------------------------------------------------------------


@router.get("/notifications")
def get_notifications(recipient_role: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"notifications": steward_notification_service.combined_notifications(db, _tenant(current_user), recipient_role=recipient_role)}


@router.get("/escalations")
def get_escalations(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"escalations": steward_escalation_service.evaluate_escalations(db, _tenant(current_user))}


# ---------------------------------------------------------------------------
# Section 26 — Reports
# ---------------------------------------------------------------------------


@router.get("/actions/{action_id}/reports/{report_type}")
def get_action_report(
    action_id: int, report_type: str, export_format: str = Query("pdf"),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        data = steward_reports_service.export_action_report(db, _tenant(current_user), action_id, report_type, export_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=data, media_type=_MEDIA_TYPES.get(export_format, "application/octet-stream"))


@router.get("/reports/{report_type}")
def get_tenant_report(
    report_type: str, export_format: str = Query("pdf"), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        data = steward_reports_service.export_tenant_report(db, _tenant(current_user), report_type, export_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=data, media_type=_MEDIA_TYPES.get(export_format, "application/octet-stream"))
