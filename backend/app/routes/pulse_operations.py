"""v4.2 — LumenAI OS: Project Pulse — Real-Time Operations Center & Live
Clinical Intelligence routes.

Frontend route: /pulse.
API prefix: /api/pulse.

  * GET /command-center                                              — Section 1
  * GET /events                                                       — Section 2
  * GET /map, GET /map/facilities/{system_id}/{facility_id}           — Section 3
  * GET /kpis                                                         — Section 4
  * POST /alerts/generate, GET /alerts, POST /alerts/{id}/acknowledge|
    resolve                                                           — Section 5
  * GET /executive                                                    — Section 6
  * GET /workflow-monitor, GET /workflow-monitor/{execution_id}       — Section 7
  * GET /ai-ops                                                       — Section 8
  * GET /facility-console                                            — Section 9
  * GET /notifications, POST /notifications/route, POST
    /notifications/send                                               — Section 10
  * GET /replay/shift, GET /replay/day, GET /replay/incident/{alert_id} — Section 11
  * GET /widgets, GET /dashboard-layout, POST /dashboard-layout        — Section 12
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.services import (
    pulse_ai_ops_service,
    pulse_alert_service,
    pulse_command_center_service,
    pulse_event_service,
    pulse_executive_service,
    pulse_facility_console_service,
    pulse_kpi_service,
    pulse_map_service,
    pulse_notification_center_service,
    pulse_replay_service,
    pulse_widget_service,
    pulse_workflow_monitor_service,
)

router = APIRouter(prefix="/api/pulse", tags=["pulse"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


# ---------------------------------------------------------------------------
# Section 1 — Pulse Command Center
# ---------------------------------------------------------------------------


@router.get("/command-center")
def get_command_center(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    role = getattr(current_user, "role", "viewer")
    return pulse_command_center_service.pulse_command_center(db, tenant_id, role=role)


# ---------------------------------------------------------------------------
# Section 2 — Live Event Stream
# ---------------------------------------------------------------------------


@router.get("/events")
def get_events(
    request: Request, event_type: str = Query(""), limit: int = Query(100, le=500), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"events": pulse_event_service.live_event_stream(db, tenant_id, event_type=event_type, limit=limit)}


# ---------------------------------------------------------------------------
# Section 3 — Enterprise Command Map
# ---------------------------------------------------------------------------


@router.get("/map")
def get_command_map(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return pulse_map_service.command_map(db)


@router.get("/map/facilities/{system_id}/{facility_id}")
def get_facility_detail(system_id: str, facility_id: str, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    result = pulse_map_service.facility_detail(db, system_id, facility_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Facility '{facility_id}' not found in system '{system_id}'.")
    return result


# ---------------------------------------------------------------------------
# Section 4 — Live Operational KPIs
# ---------------------------------------------------------------------------


@router.get("/kpis")
def get_kpis(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return pulse_kpi_service.live_kpis(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 5 — Pulse Alert Engine
# ---------------------------------------------------------------------------


@router.post("/alerts/generate")
def post_generate_alerts(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"alerts": pulse_alert_service.generate_all_alerts(db, tenant_id)}


@router.get("/alerts")
def get_alerts(
    request: Request, status: str = Query(""), alert_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"alerts": pulse_alert_service.list_alerts(db, tenant_id, status=status, alert_type=alert_type)}


@router.post("/alerts/{alert_id}/acknowledge")
def post_acknowledge_alert(
    alert_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = pulse_alert_service.acknowledge_alert(db, tenant_id, alert_id, acknowledged_by=_actor(current_user))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return result


@router.post("/alerts/{alert_id}/resolve")
def post_resolve_alert(alert_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    tenant_id = _tenant(current_user, request)
    result = pulse_alert_service.resolve_alert(db, tenant_id, alert_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 6 — Executive Command Dashboard
# ---------------------------------------------------------------------------


@router.get("/executive")
def get_executive_dashboard(
    request: Request, facility_id: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return pulse_executive_service.executive_command_dashboard(db, tenant_id, facility_id=facility_id)


# ---------------------------------------------------------------------------
# Section 7 — Live Workflow Monitoring
# ---------------------------------------------------------------------------


@router.get("/workflow-monitor")
def get_active_workflows(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"active_workflows": pulse_workflow_monitor_service.active_workflows(db, tenant_id)}


@router.get("/workflow-monitor/{execution_id}")
def get_workflow_monitor_detail(execution_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    result = pulse_workflow_monitor_service.monitor_execution(db, execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 8 — AI Operations Monitor
# ---------------------------------------------------------------------------


@router.get("/ai-ops")
def get_ai_ops(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return pulse_ai_ops_service.ai_operations_monitor(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 9 — Facility Command Console
# ---------------------------------------------------------------------------


@router.get("/facility-console")
def get_facility_console(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return pulse_facility_console_service.facility_console(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 10 — Notification Center
# ---------------------------------------------------------------------------


@router.get("/notifications")
def get_notifications(
    request: Request, role: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return pulse_notification_center_service.notification_center_feed(db, tenant_id, role=role)


@router.post("/notifications/route")
def post_route_notification(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"dispatched": pulse_notification_center_service.route_notification(db, tenant_id, payload.get("context", {}))}


@router.post("/notifications/send")
def post_send_notification(payload: dict, current_user=Depends(require_roles(*_LEADERSHIP_ROLES))):
    try:
        return pulse_notification_center_service.send_via_channel(
            payload["channel"], title=payload.get("title", ""), message=payload.get("message", ""),
            severity=payload.get("severity", "medium"), recipient=payload.get("recipient", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 11 — Operational Replay
# ---------------------------------------------------------------------------


@router.get("/replay/shift")
def get_replay_shift(
    request: Request, shift_start: str = Query(...), shift_hours: int = Query(8), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return pulse_replay_service.replay_shift(db, tenant_id, datetime.fromisoformat(shift_start), shift_hours=shift_hours)


@router.get("/replay/day")
def get_replay_day(
    request: Request, day_start: str = Query(...), db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return pulse_replay_service.replay_day(db, tenant_id, datetime.fromisoformat(day_start))


@router.get("/replay/incident/{alert_id}")
def get_replay_incident(
    alert_id: int, request: Request, window_hours: int = Query(4), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = pulse_replay_service.replay_incident(db, tenant_id, alert_id, window_hours=window_hours)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 12 — Command Widgets
# ---------------------------------------------------------------------------


@router.get("/widgets")
def get_widgets(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"widgets": pulse_widget_service.list_widgets(db)}


@router.get("/dashboard-layout")
def get_dashboard_layout(
    request: Request, is_mobile: bool = Query(False), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return pulse_widget_service.get_layout(db, tenant_id, _actor(current_user), is_mobile=is_mobile)


@router.post("/dashboard-layout")
def post_dashboard_layout(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return pulse_widget_service.save_layout(
            db, tenant_id, _actor(current_user), payload.get("layout", []), is_mobile=payload.get("is_mobile", False),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
