"""v3.0 — Project Sentinel: Autonomous Clinical Intelligence Orchestration routes.

Route: /sentinel (frontend). API prefix: /api/sentinel.

  * POST /scan                                            — Section 1
  * GET /risk-signals, POST /risk-signals/detect,
    POST /risk-signals/{id}/resolve                       — Section 2
  * GET /watchlist, POST /watchlist/refresh,
    POST /watchlist/{id}/resolve                           — Section 3
  * GET /ai-health                                         — Section 4
  * GET /digital-twin-flags, POST /digital-twin-flags/monitor,
    POST /digital-twin-flags/{id}/resolve                  — Section 5
  * GET /supervisor-intelligence                           — Section 6
  * GET /dashboard                                         — Section 7
  * GET /recommendations, POST /recommendations/generate,
    POST /recommendations/{id}/action|dismiss              — Section 8
  * GET /alerts, POST /alerts/generate,
    POST /alerts/{id}/acknowledge|resolve                  — Section 9
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.sentinel_orchestration import WATCHLIST_ENTITY_TYPES
from app.services import (
    sentinel_ai_health_service,
    sentinel_alert_service,
    sentinel_dashboard_service,
    sentinel_digital_twin_monitor_service,
    sentinel_engine_service,
    sentinel_recommendation_service,
    sentinel_risk_monitor_service,
    sentinel_supervisor_intelligence_service,
    sentinel_watchlist_service,
)

router = APIRouter(prefix="/api/sentinel", tags=["sentinel"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


# ---------------------------------------------------------------------------
# Section 1 — Sentinel Intelligence Engine
# ---------------------------------------------------------------------------


@router.post("/scan")
def post_scan(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = sentinel_engine_service.run_sentinel_scan(db, tenant_id)
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="sentinel.scan_run", resource_type="sentinel_scan", resource_id="",
        details={"enterprise_risk_score": result["enterprise_risk_score"], "alerts_count": result["alerts_count"]},
    )
    return result


# ---------------------------------------------------------------------------
# Section 2 — Continuous Risk Monitor
# ---------------------------------------------------------------------------


@router.post("/risk-signals/detect")
def post_detect_risk_signals(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"signals": sentinel_risk_monitor_service.detect_risk_signals(db, tenant_id)}


@router.get("/risk-signals")
def get_risk_signals(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"signals": sentinel_risk_monitor_service.list_open_signals(db, tenant_id)}


@router.post("/risk-signals/{signal_id}/resolve")
def post_resolve_risk_signal(
    signal_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = sentinel_risk_monitor_service.resolve_signal(db, tenant_id, signal_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Risk signal {signal_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 3 — Clinical Watchlists
# ---------------------------------------------------------------------------


@router.post("/watchlist/refresh")
def post_refresh_watchlist(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"watchlist": sentinel_watchlist_service.refresh_watchlists(db, tenant_id)}


@router.get("/watchlist")
def get_watchlist(
    request: Request, entity_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    if entity_type and entity_type not in WATCHLIST_ENTITY_TYPES:
        raise HTTPException(status_code=422, detail=f"entity_type must be one of {WATCHLIST_ENTITY_TYPES}")
    tenant_id = _tenant(current_user, request)
    return {"watchlist": sentinel_watchlist_service.list_active_watchlist(db, tenant_id, entity_type=entity_type)}


@router.post("/watchlist/{entry_id}/resolve")
def post_resolve_watchlist_entry(
    entry_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = sentinel_watchlist_service.resolve_watchlist_entry(db, tenant_id, entry_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Watchlist entry {entry_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 4 — AI Health Monitor
# ---------------------------------------------------------------------------


@router.get("/ai-health")
def get_ai_health(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return sentinel_ai_health_service.compute_ai_health(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 5 — Digital Twin Monitoring
# ---------------------------------------------------------------------------


@router.post("/digital-twin-flags/monitor")
def post_monitor_digital_twins(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"flags": sentinel_digital_twin_monitor_service.monitor_digital_twins(db, tenant_id)}


@router.get("/digital-twin-flags")
def get_digital_twin_flags(
    request: Request, tier: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"flags": sentinel_digital_twin_monitor_service.list_open_flags(db, tenant_id, tier=tier)}


@router.post("/digital-twin-flags/{flag_id}/resolve")
def post_resolve_digital_twin_flag(
    flag_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = sentinel_digital_twin_monitor_service.resolve_flag(db, tenant_id, flag_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Digital Twin flag {flag_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 6 — Supervisor Intelligence
# ---------------------------------------------------------------------------


@router.get("/supervisor-intelligence")
def get_supervisor_intelligence(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return sentinel_supervisor_intelligence_service.supervisor_intelligence_summary(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 7 — Executive Sentinel Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard")
def get_dashboard(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return sentinel_dashboard_service.executive_sentinel_dashboard(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 8 — Recommendation Engine
# ---------------------------------------------------------------------------


@router.post("/recommendations/generate")
def post_generate_recommendations(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"recommendations": sentinel_recommendation_service.generate_recommendations(db, tenant_id)}


@router.get("/recommendations")
def get_recommendations(
    request: Request, status: str = Query("open"), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"recommendations": sentinel_recommendation_service.list_recommendations(db, tenant_id, status=status)}


@router.post("/recommendations/{recommendation_id}/action")
def post_action_recommendation(
    recommendation_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = sentinel_recommendation_service.action_recommendation(db, tenant_id, recommendation_id, actioned_by=_actor(current_user))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found.")
    return result


@router.post("/recommendations/{recommendation_id}/dismiss")
def post_dismiss_recommendation(
    recommendation_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = sentinel_recommendation_service.dismiss_recommendation(db, tenant_id, recommendation_id, actioned_by=_actor(current_user))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 9 — Enterprise Alert Center
# ---------------------------------------------------------------------------


@router.post("/alerts/generate")
def post_generate_alerts(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"alerts": sentinel_alert_service.generate_enterprise_alerts(db, tenant_id)}


@router.get("/alerts")
def get_alerts(
    request: Request, severity: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"alerts": sentinel_alert_service.list_alerts(db, tenant_id, severity=severity)}


@router.post("/alerts/{alert_id}/acknowledge")
def post_acknowledge_alert(
    alert_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = sentinel_alert_service.acknowledge_alert(db, tenant_id, alert_id, acknowledged_by=_actor(current_user))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return result


@router.post("/alerts/{alert_id}/resolve")
def post_resolve_alert(
    alert_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = sentinel_alert_service.resolve_alert(db, tenant_id, alert_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return result
