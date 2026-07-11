"""LumenAI AI Specialist — Project Vulcan: Instrument Reliability, Failure
Analysis & Repair Intelligence routes.

Frontend route: /instrument-forensics. API prefix: /api/vulcan.

Uses `tenant_authz.require_tenant_roles` (real `TenantMembership`
verification), consistent with Athena/Phoenix/Infinity/Olympus/GuardianX/
Genesis AI/Nova.

  * POST /assess, GET /assessments/{id}                                — Sections 1, 7, 8, 15
  * GET  /taxonomy                                                     — Section 2
  * GET  /progression, GET /anatomy-zones                              — Sections 3, 4
  * GET  /repair-effectiveness                                         — Section 5
  * GET  /forensics/{instrument_identity}, GET /forensics/search        — Section 9
  * GET  /watchlists, GET /watchlists/{name}                            — Section 10
  * POST /feedback/{assessment_id}, GET /feedback/{assessment_id}       — Section 13
  * GET  /executive-summary                                            — Section 14
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.vulcan_reliability import VulcanReliabilityAssessment
from app.services import (
    vulcan_anatomy_zone_service,
    vulcan_executive_analytics_service,
    vulcan_failure_taxonomy_service,
    vulcan_feedback_service,
    vulcan_forensics_service,
    vulcan_progression_service,
    vulcan_reliability_agent_service,
    vulcan_repair_effectiveness_service,
    vulcan_watchlist_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/vulcan", tags=["vulcan"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


# ---------------------------------------------------------------------------
# Sections 1, 7, 8, 15 — Reliability Agent orchestrator + audit trail
# ---------------------------------------------------------------------------


@router.post("/assess", status_code=201)
def post_assess(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    instrument_identity = payload.get("instrument_identity", "")
    if not instrument_identity:
        raise HTTPException(status_code=422, detail="instrument_identity is required")
    row = vulcan_reliability_agent_service.run_reliability_assessment(
        db, tenant_id, instrument_identity,
        instrument_type=payload.get("instrument_type", ""),
        supervisor_concern=bool(payload.get("supervisor_concern", False)),
        digital_twin_version=payload.get("digital_twin_version", ""),
        baseline_version=payload.get("baseline_version", ""),
        anatomy_profile_version=payload.get("anatomy_profile_version", ""),
    )
    return vulcan_reliability_agent_service.to_dict(row)


@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    row = (
        db.query(VulcanReliabilityAssessment)
        .filter(VulcanReliabilityAssessment.id == assessment_id, VulcanReliabilityAssessment.tenant_id == _tenant(current_user))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Vulcan assessment not found")
    return vulcan_reliability_agent_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 2 — Instrument Failure Taxonomy
# ---------------------------------------------------------------------------


@router.get("/taxonomy")
def get_taxonomy(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES))):
    return vulcan_failure_taxonomy_service.taxonomy_tree()


# ---------------------------------------------------------------------------
# Sections 3, 4 — Failure Progression Model + Anatomy-Zone Reliability
# ---------------------------------------------------------------------------


@router.get("/progression")
def get_progression(
    instrument_identity: str = Query(...), zone: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return vulcan_progression_service.compute_progression(db, _tenant(current_user), instrument_identity, zone=zone or None)


@router.get("/anatomy-zones")
def get_anatomy_zones(
    instrument_identity: str = Query(...), instrument_type: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return vulcan_anatomy_zone_service.zone_reliability_analysis(db, _tenant(current_user), instrument_identity, instrument_type)


# ---------------------------------------------------------------------------
# Section 5 — Repair Effectiveness Intelligence
# ---------------------------------------------------------------------------


@router.get("/repair-effectiveness")
def get_repair_effectiveness(
    instrument_identity: str = Query(...),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"repairs": vulcan_repair_effectiveness_service.repair_history_for_instrument(db, _tenant(current_user), instrument_identity)}


# ---------------------------------------------------------------------------
# Section 9 — Instrument Forensics Workspace
# ---------------------------------------------------------------------------


@router.get("/forensics/search")
def get_forensics_search(
    manufacturer: str = Query(""), instrument_family: str = Query(""), anatomy_zone: str = Query(""),
    failure_category: str = Query(""), repair_vendor: str = Query(""), facility: str = Query(""),
    date_from: str = Query(""), date_to: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {
        "results": vulcan_forensics_service.search_forensics(
            db, _tenant(current_user), manufacturer=manufacturer, instrument_family=instrument_family,
            anatomy_zone=anatomy_zone, failure_category=failure_category, repair_vendor=repair_vendor,
            facility=facility,
            date_from=datetime.fromisoformat(date_from) if date_from else None,
            date_to=datetime.fromisoformat(date_to) if date_to else None,
        )
    }


@router.get("/forensics/{instrument_identity}")
def get_forensics_record(
    instrument_identity: str, instrument_type: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return vulcan_forensics_service.instrument_forensics_record(db, _tenant(current_user), instrument_identity, instrument_type)


# ---------------------------------------------------------------------------
# Section 10 — Reliability Watchlists
# ---------------------------------------------------------------------------


@router.get("/watchlists")
def get_watchlists(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return {name: fn(db, tenant_id) for name, fn in vulcan_watchlist_service.WATCHLISTS.items()}


@router.get("/watchlists/{name}")
def get_watchlist(name: str, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    result = vulcan_watchlist_service.run_watchlist(db, _tenant(current_user), name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown watchlist '{name}'")
    return {"watchlist": name, "entries": result}


# ---------------------------------------------------------------------------
# Section 13 — Supervisor and Repair Feedback
# ---------------------------------------------------------------------------


@router.post("/feedback/{assessment_id}", status_code=201)
def post_feedback(
    assessment_id: int, payload: dict,
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    try:
        feedback = vulcan_feedback_service.submit_feedback(
            db, _tenant(current_user), assessment_id,
            submitted_by=_actor(current_user), submitted_role=payload.get("submitted_role", ""),
            failure_classification_correct=payload.get("failure_classification_correct"),
            anatomy_zone_correct=payload.get("anatomy_zone_correct"),
            progression_correct=payload.get("progression_correct"),
            repair_effectiveness_correct=payload.get("repair_effectiveness_correct"),
            probable_contributor_correct=payload.get("probable_contributor_correct"),
            final_disposition=payload.get("final_disposition", ""),
            supervisor_rationale=payload.get("supervisor_rationale", ""),
            repair_vendor_response=payload.get("repair_vendor_response", ""),
            manufacturer_response=payload.get("manufacturer_response", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return vulcan_feedback_service._feedback_to_dict(feedback)


@router.get("/feedback/{assessment_id}")
def get_feedback(assessment_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"feedback": vulcan_feedback_service.feedback_for_assessment(db, _tenant(current_user), assessment_id)}


# ---------------------------------------------------------------------------
# Section 14 — Executive Reliability Analytics
# ---------------------------------------------------------------------------


@router.get("/executive-summary")
def get_executive_summary(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return vulcan_executive_analytics_service.executive_summary(db, _tenant(current_user))
