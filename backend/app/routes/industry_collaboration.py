"""v3.5 — Project Beacon: Collaborative Quality Ecosystem & Industry
Intelligence Platform routes.

Frontend routes: /collaboration, /collaboration-governance.
API prefix: /api/beacon.

  * GET /collaboration/hub, GET /collaboration/participants/{organization_type},
    GET /collaboration/my-status                                     — Section 1
  * GET /manufacturer-portal(/*)                                      — Section 2 (require_manufacturer_auth)
  * GET/POST /repair-partner-portal(/*)                                — Section 3 (require_manufacturer_auth)
  * GET /standards-center, POST /standards-center/publish,
    GET /standards-center/publications/{id}/versions                  — Section 4
  * GET /evidence-exchange, POST /evidence-exchange/case-reports|
    quality-improvement-initiatives|best-practices,
    GET /evidence-exchange/for/{source_type}/{source_id}               — Section 5
  * POST /manufacturer-feedback, GET /manufacturer-feedback            — Section 6
  * POST /repair-intelligence/generate, GET /repair-intelligence       — Section 7
  * GET /industry-benchmarks, GET /industry-benchmarks/percentile(/all) — Section 8
  * GET /governance/overview, GET /governance/pending-approvals        — Section 9
  * GET /advisory-board, POST/GET /advisory-board/meetings(/*),
    POST/GET /advisory-board/action-items(/*),
    POST/GET /advisory-board/recommendations(/*)                       — Section 10
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id, require_manufacturer_auth
from app.services import (
    beacon_advisory_board_service,
    beacon_collaboration_hub_service,
    beacon_evidence_exchange_service,
    beacon_governance_service,
    beacon_industry_benchmark_service,
    beacon_manufacturer_feedback_service,
    beacon_manufacturer_portal_service,
    beacon_repair_intelligence_service,
    beacon_repair_partner_service,
    beacon_standards_service,
)

router = APIRouter(prefix="/api/beacon", tags=["beacon"])

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
# Section 1 — Industry Collaboration Hub
# ---------------------------------------------------------------------------


@router.get("/collaboration/hub")
def get_collaboration_hub(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return beacon_collaboration_hub_service.collaboration_hub_summary(db)


@router.get("/collaboration/my-status")
def get_my_participant_status(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    status = beacon_collaboration_hub_service.participant_status(db, tenant_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Tenant is not enrolled as a consortium participant.")
    return status


@router.get("/collaboration/participants/{organization_type}")
def get_participants_of_type(organization_type: str, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    try:
        return {"participants": beacon_collaboration_hub_service.participants_of_type(db, organization_type)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 2 — Manufacturer Intelligence Portal
# ---------------------------------------------------------------------------


@router.get("/manufacturer-portal")
def get_manufacturer_portal(db: Session = Depends(get_db), manufacturer_id: str = Depends(require_manufacturer_auth)):
    return beacon_manufacturer_portal_service.manufacturer_portal_dashboard(db, manufacturer_id)


@router.get("/manufacturer-portal/approved-baselines")
def get_manufacturer_baselines(db: Session = Depends(get_db), manufacturer_id: str = Depends(require_manufacturer_auth)):
    return {"baselines": beacon_manufacturer_portal_service.approved_baseline_performance(db, manufacturer_id)}


@router.get("/manufacturer-portal/quality-trends")
def get_manufacturer_quality_trends(db: Session = Depends(get_db), manufacturer_id: str = Depends(require_manufacturer_auth)):
    return beacon_manufacturer_portal_service.anonymized_quality_trends(db, manufacturer_id)


@router.get("/manufacturer-portal/instrument-family-performance")
def get_manufacturer_family_performance(db: Session = Depends(get_db), manufacturer_id: str = Depends(require_manufacturer_auth)):
    return beacon_manufacturer_portal_service.instrument_family_performance(db, manufacturer_id)


@router.get("/manufacturer-portal/anatomy-findings")
def get_manufacturer_anatomy_findings(db: Session = Depends(get_db), manufacturer_id: str = Depends(require_manufacturer_auth)):
    return beacon_manufacturer_portal_service.common_anatomy_findings(db, manufacturer_id)


@router.get("/manufacturer-portal/corrosion-trend")
def get_manufacturer_corrosion_trend(db: Session = Depends(get_db), manufacturer_id: str = Depends(require_manufacturer_auth)):
    return beacon_manufacturer_portal_service.corrosion_trend(db, manufacturer_id)


@router.get("/manufacturer-portal/damage-patterns")
def get_manufacturer_damage_patterns(db: Session = Depends(get_db), manufacturer_id: str = Depends(require_manufacturer_auth)):
    return beacon_manufacturer_portal_service.damage_patterns(db, manufacturer_id)


@router.get("/manufacturer-portal/repair-recommendations")
def get_manufacturer_repair_recommendations(db: Session = Depends(get_db), manufacturer_id: str = Depends(require_manufacturer_auth)):
    return beacon_manufacturer_portal_service.repair_recommendations(db, manufacturer_id)


# ---------------------------------------------------------------------------
# Section 3 — Repair Partner Portal
# ---------------------------------------------------------------------------


@router.get("/repair-partner-portal")
def get_repair_partner_portal(db: Session = Depends(get_db), vendor_id: str = Depends(require_manufacturer_auth)):
    return beacon_repair_partner_service.repair_partner_portal_view(db, vendor_id)


@router.get("/repair-partner-portal/referrals")
def get_repair_partner_referrals(status: str = Query(""), db: Session = Depends(get_db), vendor_id: str = Depends(require_manufacturer_auth)):
    return {"referrals": beacon_repair_partner_service.repair_referrals(db, vendor_id, status=status)}


@router.get("/repair-partner-portal/turnaround")
def get_repair_partner_turnaround(db: Session = Depends(get_db), vendor_id: str = Depends(require_manufacturer_auth)):
    return beacon_repair_partner_service.repair_turnaround(db, vendor_id)


@router.get("/repair-partner-portal/repeat-analysis")
def get_repair_partner_repeat_analysis(db: Session = Depends(get_db), vendor_id: str = Depends(require_manufacturer_auth)):
    return beacon_repair_partner_service.repeat_repair_analysis(db, vendor_id)


@router.get("/repair-partner-portal/digital-twin-history/{instrument_identity}")
def get_repair_partner_digital_twin_history(
    instrument_identity: str, db: Session = Depends(get_db), vendor_id: str = Depends(require_manufacturer_auth),
):
    return {"flow_history": beacon_repair_partner_service.digital_twin_history(db, vendor_id, instrument_identity)}


@router.post("/repair-partner-portal/repairs/{repair_id}/record-outcome")
def post_record_repair_outcome(
    repair_id: int, payload: dict, db: Session = Depends(get_db), vendor_id: str = Depends(require_manufacturer_auth),
):
    try:
        return beacon_repair_partner_service.record_repair_outcome(db, vendor_id, repair_id, notes=payload.get("notes", ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 4 — Standards Collaboration Center
# ---------------------------------------------------------------------------


@router.get("/standards-center")
def get_standards_center(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return beacon_standards_service.standards_center_summary(db)


@router.post("/standards-center/publish")
def post_publish_guidance(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = beacon_standards_service.publish_guidance(
            db, tenant_id, title=payload["title"], publication_type=payload.get("publication_type", "guidance"),
            abstract=payload.get("abstract", ""), authors=payload.get("authors", []),
            regulatory_bodies_aligned=payload.get("regulatory_bodies_aligned", []),
            supersedes_id=payload.get("supersedes_id"),
        )
    except beacon_standards_service.NotAuthorizedPublisherError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, _actor(current_user), "beacon.standards_published", "beacon_standards_publications", str(result["id"]), {"title": payload["title"]})
    return result


@router.get("/standards-center/publications/{publication_id}/versions")
def get_publication_versions(publication_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"versions": beacon_standards_service.version_history(db, publication_id)}


# ---------------------------------------------------------------------------
# Section 5 — Clinical Evidence Exchange
# ---------------------------------------------------------------------------


@router.get("/evidence-exchange")
def get_evidence_exchange(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return beacon_evidence_exchange_service.evidence_exchange_summary(db, tenant_id)


@router.post("/evidence-exchange/case-reports")
def post_case_report(payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return beacon_evidence_exchange_service.submit_case_report(
        db, title=payload["title"], citation_text=payload["citation_text"], source=payload.get("source", ""),
        tenant_id=tenant_id if payload.get("private", False) else "", added_by=_actor(current_user),
    )


@router.post("/evidence-exchange/quality-improvement-initiatives")
def post_quality_improvement_initiative(payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return beacon_evidence_exchange_service.submit_quality_improvement_initiative(
        db, title=payload["title"], citation_text=payload["citation_text"], source=payload.get("source", ""),
        tenant_id=tenant_id if payload.get("private", False) else "", added_by=_actor(current_user),
    )


@router.post("/evidence-exchange/best-practices")
def post_best_practice(payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return beacon_evidence_exchange_service.submit_best_practice(
        db, title=payload["title"], citation_text=payload["citation_text"], source=payload.get("source", ""),
        tenant_id=tenant_id if payload.get("private", False) else "", added_by=_actor(current_user),
    )


@router.get("/evidence-exchange/for/{source_type}/{source_id}")
def get_evidence_for_recommendation(source_type: str, source_id: str, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"evidence": beacon_evidence_exchange_service.evidence_for_recommendation(db, source_type, source_id)}


# ---------------------------------------------------------------------------
# Section 6 — Manufacturer Feedback Loop
# ---------------------------------------------------------------------------


@router.post("/manufacturer-feedback")
def post_manufacturer_feedback(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = beacon_manufacturer_feedback_service.submit_feedback(
            db, tenant_id, category=payload["category"], title=payload["title"], body=payload["body"],
            submitted_by=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, _actor(current_user), "beacon.feedback_submitted", "horizon_knowledge_contribution", str(result["id"]), {"category": payload["category"]})
    return result


@router.get("/manufacturer-feedback")
def get_manufacturer_feedback(category: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return beacon_manufacturer_feedback_service.manufacturer_feed(db, category=category)


# ---------------------------------------------------------------------------
# Section 7 — Repair Intelligence
# ---------------------------------------------------------------------------


@router.post("/repair-intelligence/generate")
def post_generate_repair_intelligence(db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    return {"snapshots": beacon_repair_intelligence_service.generate_all_snapshots(db)}


@router.get("/repair-intelligence")
def get_repair_intelligence(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return beacon_repair_intelligence_service.repair_intelligence_summary(db)


# ---------------------------------------------------------------------------
# Section 8 — Industry Benchmarking
# ---------------------------------------------------------------------------


@router.get("/industry-benchmarks")
def get_industry_benchmarks(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return beacon_industry_benchmark_service.industry_benchmarks(db)


@router.get("/industry-benchmarks/percentile/all")
def get_industry_benchmark_percentile_all(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return beacon_industry_benchmark_service.tenant_percentile_all(db, tenant_id)


@router.get("/industry-benchmarks/percentile")
def get_industry_benchmark_percentile(
    request: Request, metric_name: str = Query(...), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return beacon_industry_benchmark_service.tenant_percentile(db, tenant_id, metric_name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 9 — Collaboration Governance
# ---------------------------------------------------------------------------


@router.get("/governance/overview")
def get_governance_overview(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return beacon_governance_service.governance_overview(db, tenant_id)


@router.get("/governance/pending-approvals")
def get_governance_pending_approvals(db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    return {"pending": beacon_governance_service.pending_knowledge_approvals(db)}


# ---------------------------------------------------------------------------
# Section 10 — Industry Advisory Board
# ---------------------------------------------------------------------------


@router.get("/advisory-board")
def get_advisory_board(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return beacon_advisory_board_service.advisory_board_summary(db)


@router.post("/advisory-board/meetings")
def post_schedule_meeting(payload: dict, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    return beacon_advisory_board_service.schedule_meeting(
        db, title=payload["title"], scheduled_at=datetime.fromisoformat(payload["scheduled_at"]),
        attendee_organizations=payload.get("attendee_organizations", []),
    )


@router.get("/advisory-board/meetings")
def get_meetings(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"meetings": beacon_advisory_board_service.list_meetings(db)}


@router.post("/advisory-board/meetings/{meeting_id}/notes")
def post_meeting_notes(meeting_id: int, payload: dict, current_user=Depends(require_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    result = beacon_advisory_board_service.record_meeting_notes(
        db, meeting_id, meeting_notes=payload.get("meeting_notes", ""), roadmap_feedback=payload.get("roadmap_feedback", ""),
        recorded_by=_actor(current_user),
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found.")
    return result


@router.post("/advisory-board/action-items")
def post_action_item(payload: dict, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    due_date = datetime.fromisoformat(payload["due_date"]) if payload.get("due_date") else None
    return beacon_advisory_board_service.add_action_item(
        db, payload["meeting_id"], description=payload["description"], owner=payload.get("owner", ""), due_date=due_date,
    )


@router.get("/advisory-board/action-items")
def get_action_items(meeting_id: int | None = Query(None), status: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"action_items": beacon_advisory_board_service.list_action_items(db, meeting_id=meeting_id, status=status)}


@router.post("/advisory-board/action-items/{item_id}/resolve")
def post_resolve_action_item(item_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    result = beacon_advisory_board_service.resolve_action_item(db, item_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Action item {item_id} not found.")
    return result


@router.post("/advisory-board/recommendations")
def post_recommendation(payload: dict, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    return beacon_advisory_board_service.propose_recommendation(
        db, title=payload["title"], rationale=payload.get("rationale", ""), target_area=payload.get("target_area", ""),
        meeting_id=payload.get("meeting_id"), review_cycle=payload.get("review_cycle", ""),
    )


@router.get("/advisory-board/recommendations")
def get_recommendations(status: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"recommendations": beacon_advisory_board_service.list_recommendations(db, status=status)}


@router.post("/advisory-board/recommendations/{recommendation_id}/decide")
def post_decide_recommendation(recommendation_id: int, payload: dict, current_user=Depends(require_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        result = beacon_advisory_board_service.decide_recommendation(
            db, recommendation_id, status=payload["status"], decided_by=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found.")
    return result
