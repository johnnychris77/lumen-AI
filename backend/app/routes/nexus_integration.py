"""v3.2 — Project Nexus: Connected Healthcare Intelligence Platform routes.

Route: /integrations (frontend). API prefix: /api/nexus. The versioned
public API gateway (Section 7) lives in a separate file,
`app/routes/nexus_api_gateway.py` (`/api/v1/*`), since those paths are
deliberately unprefixed by feature name.

  * GET /catalog                                                    — Section 1 & 2
  * POST /connectors, GET /connectors, GET /connectors/{id},
    POST /connectors/{id}/enable|disable, POST /connectors/{id}/version — Section 1 & 2
  * POST /connectors/{id}/credentials, GET .../credentials,
    POST .../credentials/{cred_id}/revoke                            — Section 10
  * POST /connectors/{id}/health-check, GET /connectors/{id}/errors,
    GET /connectors/{id}/sync-runs                                   — Section 1 & 8
  * POST /connectors/{id}/sync/assets, GET .../synced-assets          — Section 3 & 9
  * POST /connectors/{id}/sync/work-queue, GET .../work-queue-links   — Section 4
  * POST /connectors/{id}/identity-mappings, GET .../identity-mappings,
    POST /identity/resolve-role                                      — Section 5
  * POST /events/publish, GET /events,
    POST /events/subscriptions, GET /events/subscriptions             — Section 6
  * GET /dashboard                                                    — Section 8
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.services import (
    nexus_asset_sync_service,
    nexus_credential_service,
    nexus_event_bus_service,
    nexus_health_service,
    nexus_identity_service,
    nexus_registry_service,
    nexus_work_queue_sync_service,
)
from app.services.nexus_connectors.adapters import get_adapter
from app.services.nexus_work_queue_sync_service import UnknownInternalReferenceError

router = APIRouter(prefix="/api/nexus", tags=["nexus"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


def _get_connector_or_404(db: Session, tenant_id: str, connector_id: int):
    row = nexus_registry_service.get_connector(db, tenant_id, connector_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found.")
    return row


# ---------------------------------------------------------------------------
# Section 1 & 2 — Connector Registry, Framework & Versioning
# ---------------------------------------------------------------------------


@router.get("/catalog")
def get_catalog(current_user=Depends(require_roles(*_ALL_ROLES))):
    return {"catalog": nexus_registry_service.list_catalog()}


@router.post("/connectors")
def post_register_connector(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = nexus_registry_service.register_connector(db, tenant_id, connector_key=payload["connector_key"], config_json=payload.get("config_json", "{}"))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="nexus.connector_registered", resource_type="nexus_connector", resource_id=str(result["id"]),
        details={"connector_key": payload["connector_key"]},
    )
    return result


@router.get("/connectors")
def get_connectors(
    request: Request, category: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"connectors": nexus_registry_service.list_connectors(db, tenant_id, category=category)}


@router.get("/connectors/{connector_id}")
def get_connector(
    connector_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = _get_connector_or_404(db, tenant_id, connector_id)
    return nexus_registry_service.to_dict(row)


@router.post("/connectors/{connector_id}/enable")
def post_enable_connector(
    connector_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = nexus_registry_service.set_connector_status(db, tenant_id, connector_id, status="enabled")
    if result is None:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found.")
    return result


@router.post("/connectors/{connector_id}/disable")
def post_disable_connector(
    connector_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = nexus_registry_service.set_connector_status(db, tenant_id, connector_id, status="disabled")
    if result is None:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found.")
    return result


@router.post("/connectors/{connector_id}/version")
def post_set_connector_version(
    connector_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = nexus_registry_service.set_connector_version(db, tenant_id, connector_id, version=payload["version"])
    if result is None:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 10 — Integration Security: connector credentials
# ---------------------------------------------------------------------------


@router.post("/connectors/{connector_id}/credentials")
def post_issue_credential(
    connector_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    _get_connector_or_404(db, tenant_id, connector_id)
    result = nexus_credential_service.issue_credential(
        db, tenant_id, connector_id, scopes=payload.get("scopes", []), issued_by=_actor(current_user),
    )
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="nexus.credential_issued", resource_type="nexus_connector_credential", resource_id=str(result["id"]),
        details={"connector_id": connector_id},
    )
    return result


@router.get("/connectors/{connector_id}/credentials")
def get_credentials(
    connector_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"credentials": nexus_credential_service.list_credentials(db, tenant_id, connector_id)}


@router.post("/connectors/{connector_id}/credentials/{credential_id}/revoke")
def post_revoke_credential(
    connector_id: int, credential_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = nexus_credential_service.revoke_credential(db, tenant_id, credential_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found.")
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="nexus.credential_revoked", resource_type="nexus_connector_credential", resource_id=str(credential_id),
        details={"connector_id": connector_id},
    )
    return result


# ---------------------------------------------------------------------------
# Section 1 & 8 — Connection Health & Monitoring
# ---------------------------------------------------------------------------


@router.post("/connectors/{connector_id}/health-check")
def post_health_check(
    connector_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    connector = _get_connector_or_404(db, tenant_id, connector_id)
    has_credential = any(not c["revoked"] for c in nexus_credential_service.list_credentials(db, tenant_id, connector_id))
    import json
    adapter = get_adapter(connector.connector_key, tenant_id, "", json.loads(connector.config_json or "{}"), has_credential=has_credential)
    probe = adapter.test_connection()
    return nexus_health_service.record_health_check(db, tenant_id, connector, latency_ms=probe["latency_ms"])


@router.get("/connectors/{connector_id}/errors")
def get_connector_errors(
    connector_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"errors": nexus_health_service.list_errors(db, tenant_id, connector_id)}


@router.get("/connectors/{connector_id}/sync-runs")
def get_sync_runs(
    connector_id: int, request: Request, run_type: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"sync_runs": nexus_health_service.list_sync_runs(db, tenant_id, connector_id, run_type=run_type)}


@router.get("/dashboard")
def get_dashboard(request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    tenant_id = _tenant(current_user, request)
    return nexus_health_service.integration_monitoring_dashboard(db, tenant_id)


# ---------------------------------------------------------------------------
# Section 3 & 9 — Instrument Data Synchronization & Provenance
# ---------------------------------------------------------------------------


@router.post("/connectors/{connector_id}/sync/assets")
def post_sync_assets(
    connector_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    connector = _get_connector_or_404(db, tenant_id, connector_id)
    try:
        result = nexus_asset_sync_service.sync_assets(
            db, tenant_id, connector, asset_type=payload.get("asset_type", "instrument"),
            external_records=payload.get("external_records", []), facility_id=payload.get("facility_id", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Sync failed: {exc}") from exc
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="nexus.assets_synced", resource_type="nexus_connector", resource_id=str(connector_id),
        details={"processed": result["processed"], "failed": result["failed"], "conflicts": result["conflicts"]},
    )
    return result


@router.get("/connectors/{connector_id}/synced-assets")
def get_synced_assets(
    connector_id: int, request: Request, asset_type: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"assets": nexus_asset_sync_service.list_synced_assets(db, tenant_id, connector_id, asset_type=asset_type)}


# ---------------------------------------------------------------------------
# Section 4 — Work Queue Synchronization
# ---------------------------------------------------------------------------


@router.post("/connectors/{connector_id}/sync/work-queue")
def post_sync_work_queue(
    connector_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    _get_connector_or_404(db, tenant_id, connector_id)
    try:
        result = nexus_work_queue_sync_service.sync_work_queue_link(
            db, tenant_id, connector_id, queue_type=payload["queue_type"], internal_ref_id=str(payload["internal_ref_id"]),
            external_ref_id=payload.get("external_ref_id", ""), sync_direction=payload.get("sync_direction", "import_only"),
        )
    except UnknownInternalReferenceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return result


@router.get("/connectors/{connector_id}/work-queue-links")
def get_work_queue_links(
    connector_id: int, request: Request, queue_type: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"links": nexus_work_queue_sync_service.list_work_queue_links(db, tenant_id, connector_id, queue_type=queue_type)}


# ---------------------------------------------------------------------------
# Section 5 — User Identity Integration
# ---------------------------------------------------------------------------


@router.post("/connectors/{connector_id}/identity-mappings")
def post_identity_mapping(
    connector_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    _get_connector_or_404(db, tenant_id, connector_id)
    try:
        return nexus_identity_service.create_mapping(
            db, tenant_id, connector_id, external_group=payload["external_group"], mapped_role=payload["mapped_role"],
            auto_provision=payload.get("auto_provision", False),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/connectors/{connector_id}/identity-mappings")
def get_identity_mappings(
    connector_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"mappings": nexus_identity_service.list_mappings(db, tenant_id, connector_id)}


@router.post("/identity/resolve-role")
def post_resolve_role(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return nexus_identity_service.resolve_role_for_groups(db, tenant_id, payload["connector_id"], payload.get("external_groups", []))


# ---------------------------------------------------------------------------
# Section 6 — Event Bus
# ---------------------------------------------------------------------------


@router.post("/events/publish")
def post_publish_event(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return nexus_event_bus_service.publish(
            db, tenant_id=tenant_id, event_type=payload["event_type"], payload=payload.get("payload", {}), actor=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/events")
def get_events(
    request: Request, event_type: str = Query(""), limit: int = Query(50), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"events": nexus_event_bus_service.list_events(db, tenant_id, event_type=event_type, limit=limit)}


@router.post("/events/subscriptions")
def post_create_subscription(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return nexus_event_bus_service.create_subscription(
            db, tenant_id, event_type=payload["event_type"], target_type=payload["target_type"], target=payload["target"],
            connector_id=payload.get("connector_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/events/subscriptions")
def get_subscriptions(
    request: Request, event_type: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"subscriptions": nexus_event_bus_service.list_subscriptions(db, tenant_id, event_type=event_type)}


@router.post("/events/subscriptions/{subscription_id}/deactivate")
def post_deactivate_subscription(
    subscription_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = nexus_event_bus_service.deactivate_subscription(db, tenant_id, subscription_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Subscription {subscription_id} not found.")
    return result
