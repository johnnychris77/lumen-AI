"""v4.6 — LumenAI OS: Project Vanguard — Healthcare Executive
Intelligence & Strategic Decision Platform routes.

Frontend routes: /executive, /strategy.
API prefix: /api/vanguard — deliberately NOT `/api/executive` (a
pre-existing mock-KPI generator; see `app/models/vanguard_intelligence.py`
for the full naming-disambiguation note).

  * GET  /executive-intelligence                                    — Section 1
  * GET  /scorecards/{audience}, GET /scorecards/{audience}/history  — Section 2
  * GET  /financial                                                  — Section 3
  * GET  /operational                                                — Section 4
  * GET  /strategy/initiatives, GET /strategy/initiatives/{id},
    PATCH /strategy/initiatives/{id}/status,
    POST  /strategy/generate/{initiative_type}                       — Section 5
  * GET  /board-reports, POST /board-reports/generate,
    GET  /board-reports/{id}, GET /board-reports/{id}.pdf|.xlsx|.pptx — Section 7
  * GET  /benchmarking/{benchmark_type}                               — Section 8
  * GET  /governance                                                  — Section 9
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.vanguard_intelligence import BENCHMARK_TYPES, INITIATIVE_STATUSES, SCORECARD_AUDIENCES
from app.services import (
    vanguard_ai_advisor_service,  # noqa: F401  (imported for side effect: registers Executive AI Advisor intents)
    vanguard_benchmarking_service,
    vanguard_board_reporting_service,
    vanguard_executive_intelligence_service,
    vanguard_financial_service,
    vanguard_governance_service,
    vanguard_operational_service,
    vanguard_scorecard_service,
    vanguard_strategy_service,
)
from app.services.platform_org_service import facility_for_tenant

router = APIRouter(prefix="/api/vanguard", tags=["vanguard"])

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
# Section 1 — Executive Intelligence Center
# ---------------------------------------------------------------------------


@router.get("/executive-intelligence")
def get_executive_intelligence(
    request: Request, facility_id: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return vanguard_executive_intelligence_service.executive_intelligence_center(db, tenant_id, facility_id=facility_id)


# ---------------------------------------------------------------------------
# Section 2 — Executive Scorecards
# ---------------------------------------------------------------------------


@router.get("/scorecards/{audience}")
def get_scorecard(
    audience: str, request: Request, facility_id: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return vanguard_scorecard_service.generate_scorecard(db, tenant_id, audience, facility_id=facility_id)
    except vanguard_scorecard_service.UnknownScorecardAudienceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/scorecards/{audience}/history")
def get_scorecard_history(
    audience: str, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    if audience not in SCORECARD_AUDIENCES:
        raise HTTPException(status_code=422, detail=f"audience must be one of {SCORECARD_AUDIENCES}")
    tenant_id = _tenant(current_user, request)
    return {"history": vanguard_scorecard_service.scorecard_history(db, tenant_id, audience)}


# ---------------------------------------------------------------------------
# Section 3 — Financial Intelligence
# ---------------------------------------------------------------------------


@router.get("/financial")
def get_financial(
    request: Request, facility_id: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return vanguard_financial_service.financial_intelligence(db, tenant_id, facility_id=facility_id)


# ---------------------------------------------------------------------------
# Section 4 — Operational Intelligence
# ---------------------------------------------------------------------------


@router.get("/operational")
def get_operational(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return vanguard_operational_service.operational_intelligence(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 5 — Strategic Planning Workspace
# ---------------------------------------------------------------------------


@router.get("/strategy/initiatives")
def get_strategy_initiatives(
    request: Request, initiative_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"initiatives": vanguard_strategy_service.list_initiatives(db, tenant_id, initiative_type=initiative_type)}


@router.get("/strategy/initiatives/{initiative_id}")
def get_strategy_initiative(
    initiative_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return vanguard_strategy_service.get_initiative(db, tenant_id, initiative_id)
    except vanguard_strategy_service.InitiativeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/strategy/initiatives/{initiative_id}/status")
def patch_strategy_initiative_status(
    initiative_id: int, payload: dict, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    status = payload.get("status", "")
    if status not in INITIATIVE_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {INITIATIVE_STATUSES}")
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        result = vanguard_strategy_service.update_initiative_status(db, tenant_id, initiative_id, status=status)
    except vanguard_strategy_service.InitiativeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "vanguard.initiative_status_changed", "vanguard_strategic_initiatives", str(initiative_id), {"status": status})
    return result


@router.post("/strategy/generate/{initiative_type}")
def post_generate_initiative(
    initiative_type: str, payload: dict, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)

    if initiative_type == "capital_planning":
        result = vanguard_strategy_service.generate_capital_planning(db, tenant_id, created_by=actor)
    elif initiative_type == "quality_initiative":
        result = vanguard_strategy_service.generate_quality_initiative(db, tenant_id, created_by=actor)
    elif initiative_type == "service_line_expansion":
        result = vanguard_strategy_service.generate_service_line_expansion(db, tenant_id, created_by=actor)
    elif initiative_type == "capacity_planning":
        result = vanguard_strategy_service.generate_capacity_planning(db, tenant_id, facility_id=payload.get("facility_id", ""), created_by=actor)
    elif initiative_type == "scenario_planning":
        result = vanguard_strategy_service.generate_scenario_planning(
            db, tenant_id, scenario_description=payload.get("scenario_description", ""), created_by=actor,
        )
    else:
        raise HTTPException(status_code=422, detail="Unknown initiative_type for generation.")

    _audit(db, tenant_id, actor, "vanguard.initiative_generated", "vanguard_strategic_initiatives", str(result["id"]), {"initiative_type": initiative_type})
    return result


# ---------------------------------------------------------------------------
# Section 7 — Board Reporting
# ---------------------------------------------------------------------------


@router.get("/board-reports")
def get_board_reports(
    request: Request, packet_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"packets": vanguard_board_reporting_service.list_packets(db, tenant_id, packet_type=packet_type)}


@router.post("/board-reports/generate")
def post_generate_board_report(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        result = vanguard_board_reporting_service.generate_board_packet(db, tenant_id, payload.get("packet_type", ""), generated_by=actor)
    except vanguard_board_reporting_service.UnknownPacketTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "vanguard.board_report_generated", "vanguard_board_report_packets", str(result["id"]), {"packet_type": result["packet_type"]})
    return result


@router.get("/board-reports/{packet_id}.pdf")
def get_board_report_pdf(
    packet_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        packet = vanguard_board_reporting_service.get_packet(db, tenant_id, packet_id)
    except vanguard_board_reporting_service.PacketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    pdf_bytes = vanguard_board_reporting_service.build_packet_pdf_bytes(packet)
    return Response(content=pdf_bytes, media_type="application/pdf")


@router.get("/board-reports/{packet_id}.xlsx")
def get_board_report_xlsx(
    packet_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        packet = vanguard_board_reporting_service.get_packet(db, tenant_id, packet_id)
    except vanguard_board_reporting_service.PacketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    xlsx_bytes = vanguard_board_reporting_service.build_packet_xlsx_bytes(packet)
    return Response(content=xlsx_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/board-reports/{packet_id}.pptx")
def get_board_report_pptx(
    packet_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        packet = vanguard_board_reporting_service.get_packet(db, tenant_id, packet_id)
    except vanguard_board_reporting_service.PacketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    pptx_bytes = vanguard_board_reporting_service.build_packet_pptx_bytes(packet)
    return Response(content=pptx_bytes, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")


@router.get("/board-reports/{packet_id}")
def get_board_report(
    packet_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return vanguard_board_reporting_service.get_packet(db, tenant_id, packet_id)
    except vanguard_board_reporting_service.PacketNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 8 — Enterprise Benchmarking
# ---------------------------------------------------------------------------


@router.get("/benchmarking/{benchmark_type}")
def get_benchmarking(
    benchmark_type: str, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    if benchmark_type not in BENCHMARK_TYPES:
        raise HTTPException(status_code=422, detail=f"benchmark_type must be one of {BENCHMARK_TYPES}")
    tenant_id = _tenant(current_user, request)
    facility = facility_for_tenant(db, tenant_id)
    if facility is None:
        raise HTTPException(status_code=422, detail="Tenant has no enterprise-hierarchy facility to benchmark against.")
    return vanguard_benchmarking_service.compute_benchmark(db, tenant_id, facility["system_id"], benchmark_type)


# ---------------------------------------------------------------------------
# Section 9 — Governance Dashboard
# ---------------------------------------------------------------------------


@router.get("/governance")
def get_governance(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return vanguard_governance_service.governance_dashboard(db, tenant_id)
