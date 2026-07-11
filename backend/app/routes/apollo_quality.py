"""v4.7 — LumenAI OS: Project Apollo — Autonomous Clinical Quality
Management System (CQMS) routes.

Frontend route: /quality (Quality Management Center — 9 tabs).
API prefix: /api/apollo — deliberately NOT `/api/quality` (already owned by
`app/routes/quality_dashboard.py`; see `app/models/apollo_quality.py` for
the full naming-disambiguation note).

  * GET  /capa/summary, POST /capa/suggestions/create,
    POST  /capa/complaints, GET /capa/complaints,
    POST  /capa/complaints/{id}/link, POST /capa/complaints/{id}/close  — Section 2
  * GET  /rca/five-whys/{draft_id}, GET /rca/fishbone/{draft_id},
    GET  /rca/pareto, GET /rca/trend, GET /rca/summary                  — Section 3
  * GET  /audit/summary, POST /audit/generate                            — Section 4
  * GET  /competency/summary, POST /competency/annual,
    POST  /competency/procedure-validation, POST /competency/simulation,
    POST  /competency/knowledge-contribution                             — Section 5
  * POST /policies, GET /policies, GET /policies/{id},
    POST  /policies/{id}/publish, GET /policies/{id}/history,
    GET   /policies/due-for-review                                        — Section 6
  * GET  /standards/library                                                — Section 7
  * POST /improvement-projects, GET /improvement-projects,
    PATCH /improvement-projects/{id}, GET /improvement-projects/summary    — Section 8
  * GET  /quality-twin/{department}, GET /quality-twin/{department}/history — Section 9
  * GET  /executive-dashboard                                               — Section 10
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.apollo_quality import COMPLAINT_STATUSES, POLICY_STATUSES
from app.services import (
    apollo_audit_center_service,
    apollo_capa_engine_service,
    apollo_competency_center_service,
    apollo_executive_quality_service,
    apollo_improvement_portfolio_service,
    apollo_policy_service,
    apollo_quality_twin_service,
    apollo_rca_intelligence_service,
    apollo_standards_library_service,
)
from app.services.rca_engine_service import RCADraftNotFoundError

router = APIRouter(prefix="/api/apollo", tags=["apollo"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


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
# Section 2 — CAPA Engine
# ---------------------------------------------------------------------------


@router.get("/capa/summary")
def get_capa_summary(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return apollo_capa_engine_service.capa_engine_summary(db, tenant_id)


@router.post("/capa/suggestions/create")
def post_create_capa_from_suggestion(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    suggestion = payload.get("suggestion")
    if not suggestion:
        raise HTTPException(status_code=422, detail="payload must include 'suggestion'.")
    result = apollo_capa_engine_service.create_capa_from_suggestion_reviewed(suggestion, owner=payload.get("owner", actor))
    _audit(db, tenant_id, actor, "apollo.capa_created_from_suggestion", "capas", str(result.get("id")), {"trigger": suggestion.get("trigger")})
    return result


@router.post("/capa/complaints", status_code=201)
def post_create_complaint(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    complaint = apollo_capa_engine_service.create_complaint(
        db, tenant_id, source=payload.get("source", ""), description=payload.get("description", ""),
        severity=payload.get("severity", "medium"), instrument_type=payload.get("instrument_type", ""),
        reported_by=payload.get("reported_by", actor),
    )
    _audit(db, tenant_id, actor, "apollo.complaint_created", "apollo_customer_complaints", str(complaint.id), {"severity": complaint.severity})
    return {"id": complaint.id, "status": complaint.status, "severity": complaint.severity}


@router.get("/capa/complaints")
def get_complaints(
    request: Request, status: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    if status and status not in COMPLAINT_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {COMPLAINT_STATUSES}")
    tenant_id = _tenant(current_user, request)
    complaints = apollo_capa_engine_service.list_complaints(db, tenant_id, status=status)
    return {
        "complaints": [
            {
                "id": c.id, "created_at": c.created_at.isoformat(), "source": c.source, "description": c.description,
                "severity": c.severity, "instrument_type": c.instrument_type, "status": c.status,
                "linked_capa_id": c.linked_capa_id, "reported_by": c.reported_by,
            }
            for c in complaints
        ],
    }


@router.post("/capa/complaints/{complaint_id}/link")
def post_link_complaint(
    complaint_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    capa_id = payload.get("capa_id", "")
    if not capa_id:
        raise HTTPException(status_code=422, detail="payload must include 'capa_id'.")
    try:
        complaint = apollo_capa_engine_service.link_complaint_to_capa(db, tenant_id, complaint_id, capa_id=capa_id)
    except apollo_capa_engine_service.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "apollo.complaint_linked_to_capa", "apollo_customer_complaints", str(complaint_id), {"capa_id": capa_id})
    return {"id": complaint.id, "status": complaint.status, "linked_capa_id": complaint.linked_capa_id}


@router.post("/capa/complaints/{complaint_id}/close")
def post_close_complaint(
    complaint_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        complaint = apollo_capa_engine_service.close_complaint(db, tenant_id, complaint_id)
    except apollo_capa_engine_service.ComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "apollo.complaint_closed", "apollo_customer_complaints", str(complaint_id), {})
    return {"id": complaint.id, "status": complaint.status}


# ---------------------------------------------------------------------------
# Section 3 — Root Cause Intelligence
# ---------------------------------------------------------------------------


@router.get("/rca/five-whys/{draft_id}")
def get_five_whys(draft_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    try:
        return apollo_rca_intelligence_service.five_whys_view(db, tenant_id, draft_id)
    except RCADraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/rca/fishbone/{draft_id}")
def get_fishbone(draft_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    try:
        return apollo_rca_intelligence_service.fishbone_view(db, tenant_id, draft_id)
    except RCADraftNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/rca/pareto")
def get_pareto(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return apollo_rca_intelligence_service.pareto_view(db, tenant_id)


@router.get("/rca/trend")
def get_trend(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return apollo_rca_intelligence_service.trend_view(db, tenant_id)


@router.get("/rca/summary")
def get_rca_summary(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return apollo_rca_intelligence_service.rca_intelligence_summary(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 4 — Audit Center
# ---------------------------------------------------------------------------


@router.get("/audit/summary")
def get_audit_summary(
    request: Request, facility_id: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return apollo_audit_center_service.audit_center_summary(db, tenant_id, facility_id=facility_id)


@router.post("/audit/generate")
def post_generate_audit(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        result = apollo_audit_center_service.generate_audit(
            tenant_id, package_type=payload.get("package_type", ""), facility_id=payload.get("facility_id", ""),
            period_label=payload.get("period_label", ""), generated_by=actor, db=db,
        )
    except apollo_audit_center_service.UnsupportedAuditPackageTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "apollo.audit_package_generated", "regulatory_audit_packages", str(result.get("id")), {"package_type": result["package_type"]})
    return result


# ---------------------------------------------------------------------------
# Section 5 — Competency Center
# ---------------------------------------------------------------------------


@router.get("/competency/summary")
def get_competency_summary(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return apollo_competency_center_service.competency_center_summary(db, tenant_id)


@router.post("/competency/annual")
def post_annual_competency(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    technician = payload.get("technician", "")
    if not technician:
        raise HTTPException(status_code=422, detail="payload must include 'technician'.")
    result = apollo_competency_center_service.record_annual_competency(
        db, tenant_id=tenant_id, technician=technician, competency_area=payload.get("competency_area", ""),
    )
    _audit(db, tenant_id, actor, "apollo.annual_competency_recorded", "competency_events", technician, {"competency_area": payload.get("competency_area", "")})
    return result


@router.post("/competency/procedure-validation")
def post_procedure_validation(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    technician = payload.get("technician", "")
    if not technician:
        raise HTTPException(status_code=422, detail="payload must include 'technician'.")
    result = apollo_competency_center_service.record_procedure_validation(
        db, tenant_id=tenant_id, technician=technician, procedure_name=payload.get("procedure_name", ""),
    )
    _audit(db, tenant_id, actor, "apollo.procedure_validation_recorded", "competency_events", technician, {"procedure_name": payload.get("procedure_name", "")})
    return result


@router.post("/competency/simulation")
def post_simulation_result(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    technician = payload.get("technician", "")
    if not technician:
        raise HTTPException(status_code=422, detail="payload must include 'technician'.")
    result = apollo_competency_center_service.record_simulation_result(
        db, tenant_id=tenant_id, technician=technician, scenario=payload.get("scenario", ""),
        passed=bool(payload.get("passed", False)),
    )
    _audit(db, tenant_id, actor, "apollo.simulation_result_recorded", "competency_events", technician, {"scenario": payload.get("scenario", ""), "passed": bool(payload.get("passed", False))})
    return result


@router.post("/competency/knowledge-contribution")
def post_knowledge_contribution(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    technician = payload.get("technician", "")
    if not technician:
        raise HTTPException(status_code=422, detail="payload must include 'technician'.")
    result = apollo_competency_center_service.record_knowledge_contribution(
        db, tenant_id=tenant_id, technician=technician, topic=payload.get("topic", ""),
    )
    _audit(db, tenant_id, actor, "apollo.knowledge_contribution_recorded", "competency_events", technician, {"topic": payload.get("topic", "")})
    return result


# ---------------------------------------------------------------------------
# Section 6 — Policy Intelligence
# ---------------------------------------------------------------------------


@router.post("/policies", status_code=201)
def post_create_policy(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        result = apollo_policy_service.create_policy(
            db, tenant_id, title=payload.get("title", ""), owner=payload.get("owner", actor),
            review_date=payload.get("review_date"), content=payload.get("content", ""),
            references=payload.get("references"), linked_standards=payload.get("linked_standards"),
            affected_workflows=payload.get("affected_workflows"), affected_competencies=payload.get("affected_competencies"),
            affected_ai_rules=payload.get("affected_ai_rules"), supersedes_id=payload.get("supersedes_id"),
        )
    except apollo_policy_service.PolicyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "apollo.policy_created", "apollo_quality_policies", str(result["id"]), {"title": result["title"]})
    return result


@router.get("/policies")
def get_policies(
    request: Request, status: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    if status and status not in POLICY_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {POLICY_STATUSES}")
    tenant_id = _tenant(current_user, request)
    return {"policies": apollo_policy_service.list_policies(db, tenant_id, status=status)}


@router.get("/policies/due-for-review")
def get_policies_due_for_review(
    request: Request, within_days: int = Query(30), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"policies": apollo_policy_service.policies_due_for_review(db, tenant_id, within_days=within_days)}


@router.get("/policies/{policy_id}")
def get_policy(policy_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    try:
        return apollo_policy_service.get_policy(db, tenant_id, policy_id)
    except apollo_policy_service.PolicyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/policies/{policy_id}/publish")
def post_publish_policy(
    policy_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        result = apollo_policy_service.publish_policy(db, tenant_id, policy_id, published_by=actor)
    except apollo_policy_service.PolicyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "apollo.policy_published", "apollo_quality_policies", str(policy_id), {})
    return result


@router.get("/policies/{policy_id}/history")
def get_policy_history(policy_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"history": apollo_policy_service.version_history(db, tenant_id, policy_id)}


# ---------------------------------------------------------------------------
# Section 7 — Standards Knowledge Library
# ---------------------------------------------------------------------------


@router.get("/standards/library")
def get_standards_library(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return apollo_standards_library_service.standards_library_summary(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 8 — Continuous Improvement Portfolio
# ---------------------------------------------------------------------------


@router.post("/improvement-projects", status_code=201)
def post_create_improvement_project(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    result = apollo_improvement_portfolio_service.create_project(
        db, tenant_id=tenant_id, initiative=payload.get("initiative", ""), owner=payload.get("owner", actor),
        target_date=payload.get("target_date"), expected_impact=payload.get("expected_impact", ""),
        methodology=payload.get("methodology", ""), cost_savings_usd=payload.get("cost_savings_usd"),
        quality_improvement_metric=payload.get("quality_improvement_metric", ""),
        risk_reduction_metric=payload.get("risk_reduction_metric", ""),
        executive_visible=bool(payload.get("executive_visible", False)),
    )
    _audit(db, tenant_id, actor, "apollo.improvement_project_created", "continuous_improvement_initiatives", str(result["id"]), {"methodology": result["methodology"]})
    return result


@router.get("/improvement-projects")
def get_improvement_projects(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"projects": apollo_improvement_portfolio_service.list_projects(db, tenant_id)}


@router.get("/improvement-projects/summary")
def get_improvement_projects_summary(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return apollo_improvement_portfolio_service.portfolio_summary(db, tenant_id)


@router.patch("/improvement-projects/{project_id}")
def patch_improvement_project(
    project_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    result = apollo_improvement_portfolio_service.update_project(db, tenant_id=tenant_id, initiative_id=project_id, **payload)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Improvement project {project_id} not found for tenant {tenant_id}.")
    _audit(db, tenant_id, actor, "apollo.improvement_project_updated", "continuous_improvement_initiatives", str(project_id), payload)
    return result


# ---------------------------------------------------------------------------
# Section 9 — Quality Digital Twin
# ---------------------------------------------------------------------------


@router.get("/quality-twin/{department}")
def get_quality_twin(department: str, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return apollo_quality_twin_service.compute_quality_twin(db, tenant_id, department)


@router.get("/quality-twin/{department}/history")
def get_quality_twin_history(department: str, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"history": apollo_quality_twin_service.twin_history(db, tenant_id, department)}


# ---------------------------------------------------------------------------
# Section 10 — Executive Quality Dashboard
# ---------------------------------------------------------------------------


@router.get("/executive-dashboard")
def get_executive_dashboard(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return apollo_executive_quality_service.executive_quality_dashboard(db, tenant_id)
