"""v4.0 — LumenAI OS: Project Genesis — Platform Core routes.

Frontend routes: platform launcher (integrated into the app shell),
/platform-admin.
API prefix: /api/platform.

  * GET /identity/me                                                   — Section 1 Identity
  * GET /organizations/tree, GET /organizations/facilities             — Section 1 Org Management
  * GET /modules, GET /modules/{module_key}                             — Section 3
  * GET /licenses, POST /licenses                                      — Section 1 Licensing
  * GET /notifications                                                 — Section 1 Notification Engine
  * GET /configuration, POST /configuration                            — Section 1 Configuration
  * POST /plugins, GET /plugins, POST /plugins/{key}/activate|disable   — Section 8
  * GET /navigation/launcher, POST /navigation/recent,
    POST/DELETE /navigation/favorites/{module_key}                     — Section 4
  * GET /search                                                         — Section 5
  * GET /activity-feed                                                  — Section 6
  * GET /intelligence/services                                         — Section 2
  * GET /admin/dashboard, GET /admin/users, GET /admin/feature-flags,
    GET /admin/api-keys, GET /admin/integrations, GET /admin/audit-logs — Section 9
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.nexus_integration import EVENT_MODULE_LICENSE_CHANGED, EVENT_PLUGIN_REGISTERED
from app.models.platform_core import MODULE_KEYS
from app.services import (
    nexus_event_bus_service,
    platform_activity_feed_service,
    platform_admin_service,
    platform_configuration_service,
    platform_identity_service,
    platform_intelligence_gateway,
    platform_licensing_service,
    platform_module_registry_service,
    platform_navigation_service,
    platform_notification_service,
    platform_org_service,
    platform_plugin_service,
    platform_search_service,
)
from app.services.platform_plugin_service import DuplicatePluginKeyError, UnknownPluginError


def _publish_best_effort(db: Session, *, tenant_id: str, event_type: str, payload: dict, actor: str) -> None:
    """Publishing a platform event is a side effect, never a requirement —
    a failure here must not roll back the license/plugin change itself."""
    try:
        nexus_event_bus_service.publish(db, tenant_id=tenant_id, event_type=event_type, payload=payload, actor=actor)
    except Exception:
        pass

router = APIRouter(prefix="/api/platform", tags=["platform"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
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
# Section 1 — Identity
# ---------------------------------------------------------------------------


@router.get("/identity/me")
def get_identity_me(request: Request, current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    role = getattr(current_user, "role", "viewer")
    return platform_identity_service.identity_summary(_actor(current_user), role, tenant_id)


@router.get("/identity/roles")
def get_identity_roles(current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"roles": platform_identity_service.list_known_roles()}


# ---------------------------------------------------------------------------
# Section 1 — Organization Management
# ---------------------------------------------------------------------------


@router.get("/organizations/tree")
def get_org_tree(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return platform_org_service.organization_tree(db)


@router.get("/organizations/facilities")
def get_org_facilities(
    market_id: str = Query(""), region_id: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return {"facilities": platform_org_service.list_facilities(db, market_id=market_id, region_id=region_id)}


# ---------------------------------------------------------------------------
# Section 3 — Modular Application Framework
# ---------------------------------------------------------------------------


@router.get("/modules")
def get_modules(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"modules": platform_module_registry_service.list_modules(db)}


@router.get("/modules/{module_key}")
def get_module(module_key: str, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    result = platform_module_registry_service.get_module(db, module_key)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Module '{module_key}' not found.")
    return result


# ---------------------------------------------------------------------------
# Section 1 — Licensing
# ---------------------------------------------------------------------------


@router.get("/licenses")
def get_licenses(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"licenses": platform_licensing_service.tenant_licenses(db, tenant_id)}


@router.post("/licenses", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def post_license(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ADMIN_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = platform_licensing_service.set_license(
            db, tenant_id, payload["module_key"], status=payload["status"], granted_by=_actor(current_user),
            notes=payload.get("notes", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, _actor(current_user), "platform.license_changed", "platform_module_licenses", str(result["id"]),
           {"module_key": payload["module_key"], "status": payload["status"]})
    _publish_best_effort(
        db, tenant_id=tenant_id, event_type=EVENT_MODULE_LICENSE_CHANGED,
        payload={"module_key": payload["module_key"], "status": payload["status"]}, actor=_actor(current_user),
    )
    return result


# ---------------------------------------------------------------------------
# Section 1 — Notification Engine
# ---------------------------------------------------------------------------


@router.get("/notifications")
def get_notifications(
    request: Request, role: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"notifications": platform_notification_service.unified_notifications(db, tenant_id, recipient_role=role)}


# ---------------------------------------------------------------------------
# Section 1 — Configuration
# ---------------------------------------------------------------------------


@router.get("/configuration")
def get_configuration(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"configuration": platform_configuration_service.list_configs(db, tenant_id)}


@router.post("/configuration", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def post_configuration(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ADMIN_ROLES)),
):
    tenant_id = _tenant(current_user, request) if payload.get("scope", "tenant") == "tenant" else ""
    result = platform_configuration_service.set_config(
        db, tenant_id, payload["config_key"], payload.get("config_value", ""), updated_by=_actor(current_user),
    )
    return result


# ---------------------------------------------------------------------------
# Section 8 — Plugin Framework
# ---------------------------------------------------------------------------


@router.post("/plugins", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def post_register_plugin(
    payload: dict, request: Request, current_user=Depends(require_roles(*_ADMIN_ROLES)), db: Session = Depends(get_db),
):
    try:
        result = platform_plugin_service.register_plugin(
            db, plugin_key=payload["plugin_key"], name=payload["name"], version=payload.get("version", "0.1.0"),
            registered_by=_actor(current_user), routes=payload.get("routes", []), menus=payload.get("menus", []),
            permissions=payload.get("permissions", []), widgets=payload.get("widgets", []),
            dashboards=payload.get("dashboards", []), reports=payload.get("reports", []),
        )
    except DuplicatePluginKeyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    tenant_id = _tenant(current_user, request)
    _publish_best_effort(
        db, tenant_id=tenant_id, event_type=EVENT_PLUGIN_REGISTERED,
        payload={"plugin_key": payload["plugin_key"], "name": payload["name"]}, actor=_actor(current_user),
    )
    return result


@router.get("/plugins")
def get_plugins(status: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"plugins": platform_plugin_service.list_plugins(db, status=status)}


@router.post("/plugins/{plugin_key}/activate", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def post_activate_plugin(plugin_key: str, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ADMIN_ROLES))):
    try:
        return platform_plugin_service.activate_plugin(db, plugin_key)
    except UnknownPluginError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plugins/{plugin_key}/disable", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def post_disable_plugin(plugin_key: str, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ADMIN_ROLES))):
    try:
        return platform_plugin_service.disable_plugin(db, plugin_key)
    except UnknownPluginError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 4 — Unified Navigation
# ---------------------------------------------------------------------------


@router.get("/navigation/launcher")
def get_launcher(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    role = getattr(current_user, "role", "viewer")
    return platform_navigation_service.launcher_view(db, tenant_id, role, _actor(current_user))


@router.post("/navigation/recent")
def post_recent(payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    if payload.get("module_key") not in MODULE_KEYS:
        raise HTTPException(status_code=422, detail=f"module_key must be one of {MODULE_KEYS}")
    platform_navigation_service.record_recent_access(db, tenant_id, _actor(current_user), payload["module_key"])
    return {"status": "recorded"}


@router.post("/navigation/favorites/{module_key}")
def post_favorite(module_key: str, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    if module_key not in MODULE_KEYS:
        raise HTTPException(status_code=422, detail=f"module_key must be one of {MODULE_KEYS}")
    tenant_id = _tenant(current_user, request)
    return platform_navigation_service.add_favorite(db, tenant_id, _actor(current_user), module_key)


@router.delete("/navigation/favorites/{module_key}")
def delete_favorite(module_key: str, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    removed = platform_navigation_service.remove_favorite(db, tenant_id, _actor(current_user), module_key)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Module '{module_key}' is not a favorite.")
    return {"status": "removed"}


# ---------------------------------------------------------------------------
# Section 5 — Global Search
# ---------------------------------------------------------------------------


@router.get("/search")
def get_search(
    request: Request, q: str = Query(..., min_length=1), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return platform_search_service.global_search(db, tenant_id, q)


# ---------------------------------------------------------------------------
# Section 6 — Universal Activity Feed
# ---------------------------------------------------------------------------


@router.get("/activity-feed")
def get_activity_feed(
    request: Request, limit: int = Query(50, le=200), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"activity": platform_activity_feed_service.universal_activity_feed(db, tenant_id, limit=limit)}


# ---------------------------------------------------------------------------
# Section 2 — Shared Intelligence Layer
# ---------------------------------------------------------------------------


@router.get("/intelligence/services")
def get_intelligence_services(current_user=Depends(require_roles(*_ALL_ROLES))):
    return platform_intelligence_gateway.list_shared_services()


# ---------------------------------------------------------------------------
# Section 9 — Platform Administration
# ---------------------------------------------------------------------------


@router.get("/admin/dashboard", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def get_admin_dashboard(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ADMIN_ROLES))):
    tenant_id = _tenant(current_user, request)
    return platform_admin_service.admin_dashboard(db, tenant_id)


@router.get("/admin/users", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def get_admin_users(db: Session = Depends(get_db), current_user=Depends(require_roles(*_ADMIN_ROLES))):
    return {"users": platform_admin_service.list_users(db)}


@router.get("/admin/feature-flags", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def get_admin_feature_flags(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ADMIN_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"feature_flags": platform_admin_service.list_feature_flags(db, tenant_id)}


@router.get("/admin/api-keys", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def get_admin_api_keys(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ADMIN_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"api_keys": platform_admin_service.list_api_keys(db, tenant_id)}


@router.get("/admin/integrations", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def get_admin_integrations(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ADMIN_ROLES))):
    tenant_id = _tenant(current_user, request)
    return {"integrations": platform_admin_service.list_integrations(db, tenant_id)}


@router.get("/admin/audit-logs", dependencies=[Depends(require_roles(*_ADMIN_ROLES))])
def get_admin_audit_logs(
    request: Request, limit: int = Query(100, le=500), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ADMIN_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"audit_logs": platform_admin_service.list_audit_logs(db, tenant_id, limit=limit)}
