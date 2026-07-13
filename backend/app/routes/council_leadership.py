"""LumenAI AI Leadership Platform — Project Council: Multi-Agent
Leadership Teams & Governed Consensus Intelligence routes.

Frontend route: /council. API prefix: /api/council.

Uses `tenant_authz.require_tenant_roles` for tenant-scoped access
(Section 20 -- cross-tenant Council access is always denied, since every
query below filters by the authenticated user's own `tenant_id`).
Finalizing a human decision additionally enforces the brief's five-tier
authority scale via `council_human_decision_service.can_approve` -- a
`viewer`/`operator` ("technician") can read a Council Case but can never
finalize its decision.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.council_leadership import CASE_TYPES
from app.services import (
    council_agreement_map_service,
    council_brief_service,
    council_decision_journal_service,
    council_decision_options_service,
    council_dissent_service,
    council_human_decision_service,
    council_meeting_service,
    council_notification_service,
    council_orchestration_service,
    council_outcome_service,
    council_performance_service,
    council_reports_service,
    council_specialist_assessment_service,
    council_team_registry_service,
    council_workspace_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/council", tags=["council"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


# ---------------------------------------------------------------------------
# Sections 2 & 15 — Leadership Team Registry & Governance
# ---------------------------------------------------------------------------


@router.get("/teams")
def get_teams(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    council_team_registry_service.ensure_default_teams(db, _tenant(current_user))
    return {"teams": council_team_registry_service.list_teams(db, _tenant(current_user))}


@router.post("/teams/{team_key}")
def post_update_team(
    team_key: str, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        row = council_team_registry_service.update_team_config(
            db, _tenant(current_user), team_key,
            required_specialists=payload.get("required_specialists"), optional_specialists=payload.get("optional_specialists"),
            decision_scope=payload.get("decision_scope"), escalation_rules=payload.get("escalation_rules"),
            quorum_requirement=payload.get("quorum_requirement"), evidence_requirements=payload.get("evidence_requirements"),
            review_frequency=payload.get("review_frequency"), owner=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return council_team_registry_service.to_dict(row)


@router.get("/teams/{team_key}/history")
def get_team_history(team_key: str, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"history": council_team_registry_service.team_config_history(db, _tenant(current_user), team_key)}


# ---------------------------------------------------------------------------
# Section 1 & 3 — Council Orchestration Engine + Council Case
# ---------------------------------------------------------------------------


@router.post("/cases", status_code=201)
def post_open_case(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    case_type = payload.get("case_type", "")
    if case_type not in CASE_TYPES:
        raise HTTPException(status_code=422, detail=f"Unknown case_type '{case_type}'")
    try:
        row = council_orchestration_service.open_case(
            db, _tenant(current_user), case_type=case_type, source_event=payload.get("source_event", ""),
            inspection_ids=payload.get("inspection_ids"), instrument_ids=payload.get("instrument_ids"),
            digital_twin_refs=payload.get("digital_twin_refs"), evidence_package=payload.get("evidence_package"),
            risk_level=payload.get("risk_level", ""), urgency=payload.get("urgency", "routine"),
            requested_decision=payload.get("requested_decision", ""), facility_id=payload.get("facility_id", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return council_orchestration_service.to_dict(row)


@router.post("/cases/{council_case_id}/convene")
def post_convene(council_case_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    if council_orchestration_service.get_case(db, _tenant(current_user), council_case_id) is None:
        raise HTTPException(status_code=404, detail="Council Case not found")
    try:
        row = council_orchestration_service.convene(db, _tenant(current_user), council_case_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return council_orchestration_service.to_dict(row)


@router.get("/cases")
def get_cases(
    status: str = Query(""), case_type: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"cases": council_orchestration_service.list_cases(db, _tenant(current_user), status=status, case_type=case_type)}


@router.get("/cases/{council_case_id}")
def get_case_detail(council_case_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    case = council_orchestration_service.get_case(db, _tenant(current_user), council_case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Council Case not found")
    return {
        "case": council_orchestration_service.to_dict(case),
        "assessments": council_specialist_assessment_service.assessments_for_case(db, _tenant(current_user), council_case_id),
        "dissent": council_dissent_service.dissent_for_case(db, _tenant(current_user), council_case_id),
        "decision_options": council_decision_options_service.options_for_case(db, _tenant(current_user), council_case_id),
        "human_decisions": council_human_decision_service.decisions_for_case(db, _tenant(current_user), council_case_id),
        "agreement_map": council_agreement_map_service.build_agreement_map(db, _tenant(current_user), council_case_id),
    }


# ---------------------------------------------------------------------------
# Section 4 — Independent Specialist Assessments (revision support)
# ---------------------------------------------------------------------------


@router.get("/cases/{council_case_id}/assessments")
def get_assessments(council_case_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"assessments": council_specialist_assessment_service.assessments_for_case(db, _tenant(current_user), council_case_id)}


# ---------------------------------------------------------------------------
# Section 10 — Agreement Map
# ---------------------------------------------------------------------------


@router.get("/cases/{council_case_id}/agreement-map")
def get_agreement_map(council_case_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return council_agreement_map_service.build_agreement_map(db, _tenant(current_user), council_case_id)


# ---------------------------------------------------------------------------
# Section 8 — Human Decision Authority
# ---------------------------------------------------------------------------


@router.post("/cases/{council_case_id}/decisions", status_code=201)
def post_finalize_decision(
    council_case_id: int, payload: dict,
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    try:
        row = council_human_decision_service.finalize_decision(
            db, _tenant(current_user), council_case_id, approver=_actor(current_user),
            approver_role=current_user.get("role", ""), decision=payload.get("decision", ""),
            rationale=payload.get("rationale", ""), conditions=payload.get("conditions", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return council_human_decision_service.to_dict(row)


@router.get("/cases/{council_case_id}/decisions")
def get_decisions(council_case_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"decisions": council_human_decision_service.decisions_for_case(db, _tenant(current_user), council_case_id)}


# ---------------------------------------------------------------------------
# Section 9 — Council Workspace (`/council`)
# ---------------------------------------------------------------------------


@router.get("/workspace")
def get_workspace(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return council_workspace_service.workspace_summary(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Section 11 — Council Brief Generator
# ---------------------------------------------------------------------------


@router.get("/cases/{council_case_id}/briefs/{brief_type}")
def get_brief(
    council_case_id: int, brief_type: str,
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    resolver = {
        "supervisor": council_brief_service.supervisor_brief,
        "manager": council_brief_service.manager_brief,
        "executive": council_brief_service.executive_brief,
    }.get(brief_type)
    if resolver is None:
        raise HTTPException(status_code=422, detail=f"Unknown brief_type '{brief_type}'")
    try:
        return resolver(db, _tenant(current_user), council_case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 12 — Council Meeting Mode
# ---------------------------------------------------------------------------


@router.post("/cases/{council_case_id}/meeting-notes", status_code=201)
def post_meeting_notes(
    council_case_id: int, payload: dict,
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        row = council_meeting_service.record_meeting_notes(
            db, _tenant(current_user), council_case_id, discussion_notes=payload.get("discussion_notes", ""),
            recorded_by=payload.get("recorded_by") or _actor(current_user), action_items=payload.get("action_items"),
            owner=payload.get("owner", ""), agenda=payload.get("agenda"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return council_meeting_service.to_dict(row)


@router.get("/cases/{council_case_id}/meeting-notes")
def get_meeting_notes(council_case_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"meeting_notes": council_meeting_service.meeting_notes_for_case(db, _tenant(current_user), council_case_id)}


# ---------------------------------------------------------------------------
# Section 13 — Decision Journal Integration
# ---------------------------------------------------------------------------


@router.post("/cases/{council_case_id}/journal", status_code=201)
def post_journal_entry(
    council_case_id: int, payload: dict,
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        return council_decision_journal_service.record_council_decision(
            db, _tenant(current_user), council_case_id, leader_decision=payload.get("leader_decision", ""),
            decided_by=_actor(current_user), decided_role=current_user.get("role", ""),
            outcome=payload.get("outcome", ""), lessons_learned=payload.get("lessons_learned", ""),
            new_status=payload.get("new_status"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 14 — Outcome Effectiveness Review
# ---------------------------------------------------------------------------


@router.post("/cases/{council_case_id}/outcome-review", status_code=201)
def post_outcome_review(
    council_case_id: int, payload: dict,
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    row = council_outcome_service.record_outcome_review(
        db, _tenant(current_user), council_case_id,
        issue_resolved=payload.get("issue_resolved"), recurred=payload.get("recurred"),
        risk_decreased=payload.get("risk_decreased"), operational_performance_improved=payload.get("operational_performance_improved"),
        recommendation_followed=payload.get("recommendation_followed"), dissent_valid=payload.get("dissent_valid"),
        additional_evidence_changed_decision=payload.get("additional_evidence_changed_decision"),
        unintended_consequence=payload.get("unintended_consequence", False), notes=payload.get("notes", ""),
    )
    return council_outcome_service.to_dict(row)


@router.get("/cases/{council_case_id}/outcome-review")
def get_outcome_reviews(council_case_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"outcome_reviews": council_outcome_service.outcome_reviews_for_case(db, _tenant(current_user), council_case_id)}


# ---------------------------------------------------------------------------
# Section 17 — Specialist Performance Review
# ---------------------------------------------------------------------------


@router.get("/performance")
def get_performance(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return council_performance_service.specialist_performance_summary(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Section 18 — Notifications and Escalations
# ---------------------------------------------------------------------------


@router.get("/notifications")
def get_notifications(
    recipient_role: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"notifications": council_notification_service.combined_notifications(db, _tenant(current_user), recipient_role=recipient_role)}


# ---------------------------------------------------------------------------
# Section 19 — Reports
# ---------------------------------------------------------------------------

_MEDIA_TYPES = {"pdf": "application/pdf", "csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


@router.get("/cases/{council_case_id}/reports/{report_type}")
def get_case_report(
    council_case_id: int, report_type: str, export_format: str = Query("pdf"),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        data = council_reports_service.export_case_report(db, _tenant(current_user), council_case_id, report_type, export_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=data, media_type=_MEDIA_TYPES.get(export_format, "application/octet-stream"))


@router.get("/reports/governance")
def get_governance_report(
    export_format: str = Query("pdf"), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        data = council_reports_service.export_governance_report(db, _tenant(current_user), export_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=data, media_type=_MEDIA_TYPES.get(export_format, "application/octet-stream"))


@router.get("/reports/performance")
def get_performance_report(
    export_format: str = Query("pdf"), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        data = council_reports_service.export_performance_report(db, _tenant(current_user), export_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(content=data, media_type=_MEDIA_TYPES.get(export_format, "application/octet-stream"))
