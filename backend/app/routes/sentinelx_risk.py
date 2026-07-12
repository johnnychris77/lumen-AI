"""LumenAI AI Specialist — Project Sentinel-X: Clinical Risk Intelligence &
Patient Safety Agent routes.

Frontend route: /risk. API prefix: /api/sentinelx.

**"Sentinel" already exists** as a different, established system in this
codebase (`/api/sentinel`, `/sentinel`) -- this router deliberately uses a
distinct `/api/sentinelx` prefix to avoid any collision or confusion; see
`app/models/sentinelx_risk.py` for the full naming disambiguation.

Uses `tenant_authz.require_tenant_roles`, consistent with every sprint
since Athena (v4.8).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.sentinelx_risk import SentinelXRiskAssessment
from app.services import (
    sentinelx_dashboard_service,
    sentinelx_heatmap_service,
    sentinelx_override_service,
    sentinelx_patient_safety_watch_service,
    sentinelx_predictive_service,
    sentinelx_risk_agent_service,
    sentinelx_supervisor_workspace_service,
    sentinelx_timeline_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/sentinelx", tags=["sentinelx"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


# ---------------------------------------------------------------------------
# Section 1 — Risk Intelligence Agent
# ---------------------------------------------------------------------------


@router.post("/assess", status_code=201)
def post_assess(payload: dict, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    instrument_identity = payload.get("instrument_identity", "")
    if not instrument_identity:
        raise HTTPException(status_code=422, detail="instrument_identity is required")
    row = sentinelx_risk_agent_service.run_risk_assessment(
        db, _tenant(current_user), instrument_identity,
        instrument_type=payload.get("instrument_type", ""), inspection_id=payload.get("inspection_id"),
    )
    return sentinelx_risk_agent_service.to_dict(row)


@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    row = (
        db.query(SentinelXRiskAssessment)
        .filter(SentinelXRiskAssessment.id == assessment_id, SentinelXRiskAssessment.tenant_id == _tenant(current_user))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Sentinel-X risk assessment not found")
    return sentinelx_risk_agent_service.to_dict(row)


@router.get("/assessments")
def get_assessments(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    rows = (
        db.query(SentinelXRiskAssessment)
        .filter(SentinelXRiskAssessment.tenant_id == _tenant(current_user))
        .order_by(SentinelXRiskAssessment.created_at.desc())
        .all()
    )
    return {"assessments": [sentinelx_risk_agent_service.to_dict(r) for r in rows]}


# ---------------------------------------------------------------------------
# Section 5 — Patient Safety Watch
# ---------------------------------------------------------------------------


@router.post("/alerts/scan", status_code=201)
def post_scan_alerts(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    fired = sentinelx_patient_safety_watch_service.scan_for_alerts(db, _tenant(current_user))
    return {"alerts_fired": [sentinelx_patient_safety_watch_service.to_dict(a) for a in fired]}


@router.get("/alerts")
def get_alerts(acknowledged: bool | None = Query(None), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"alerts": sentinelx_patient_safety_watch_service.list_alerts(db, _tenant(current_user), acknowledged=acknowledged)}


@router.post("/alerts/{alert_id}/acknowledge")
def post_acknowledge_alert(alert_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    row = sentinelx_patient_safety_watch_service.acknowledge_alert(db, _tenant(current_user), alert_id, acknowledged_by=_actor(current_user))
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return sentinelx_patient_safety_watch_service.to_dict(row)


# ---------------------------------------------------------------------------
# Section 6 — Enterprise Risk Heatmaps
# ---------------------------------------------------------------------------


@router.get("/heatmaps")
def get_heatmaps(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return sentinelx_heatmap_service.all_heatmaps(db, _tenant(current_user))


@router.get("/heatmaps/{dimension}")
def get_heatmap(dimension: str, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    result = sentinelx_heatmap_service.risk_heatmap(db, _tenant(current_user), dimension)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Unknown heatmap dimension '{dimension}'")
    return {"dimension": dimension, "buckets": result}


# ---------------------------------------------------------------------------
# Section 7 — Risk Timeline
# ---------------------------------------------------------------------------


@router.get("/timeline/{instrument_identity}")
def get_timeline(instrument_identity: str, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return sentinelx_timeline_service.build_risk_timeline(db, _tenant(current_user), instrument_identity)


# ---------------------------------------------------------------------------
# Section 8 — Predictive Risk
# ---------------------------------------------------------------------------


@router.get("/predictive/{instrument_identity}")
def get_predictive(instrument_identity: str, instrument_type: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return sentinelx_predictive_service.predictive_risk_summary(db, _tenant(current_user), instrument_identity, instrument_type)


# ---------------------------------------------------------------------------
# Section 9 — Risk Dashboard (`/risk`)
# ---------------------------------------------------------------------------


@router.get("/dashboard")
def get_dashboard(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return sentinelx_dashboard_service.risk_dashboard_summary(db, _tenant(current_user))


# ---------------------------------------------------------------------------
# Section 10 — Supervisor Workspace + auditable overrides
# ---------------------------------------------------------------------------


@router.get("/supervisor-workspace")
def get_supervisor_workspace(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return sentinelx_supervisor_workspace_service.supervisor_workspace_summary(db, _tenant(current_user))


@router.post("/overrides", status_code=201)
def post_override(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        row = sentinelx_override_service.submit_override(
            db, _tenant(current_user), payload.get("assessment_id"),
            overridden_risk_level=payload.get("overridden_risk_level", ""), rationale=payload.get("rationale", ""),
            submitted_by=_actor(current_user), submitted_role=current_user.get("role", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return sentinelx_override_service.to_dict(row)


@router.get("/overrides/{assessment_id}")
def get_overrides(assessment_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"overrides": sentinelx_override_service.overrides_for_assessment(db, _tenant(current_user), assessment_id)}
