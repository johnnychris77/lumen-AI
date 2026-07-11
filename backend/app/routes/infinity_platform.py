"""v5.0 — LumenAI OS: Project Infinity — Healthcare AI Platform &
Developer Ecosystem routes.

Frontend routes: /developers, /marketplace.
API prefix: /api/infinity — free namespace (confirmed via research). The
versioned public API itself lives at `/api/v1/*`
(`nexus_api_gateway.py`, extended for this sprint) — `/api/infinity` is
the platform's own internal management surface for developer accounts,
marketplace curation, certification, billing, and sandboxing.

## Two distinct auth paths

  * **Internal tenant staff** — `tenant_authz.require_tenant_roles` (real
    `TenantMembership` verification), matching Athena (v4.8) and Phoenix
    (v4.9). Used for admin-curation actions (approving developer
    accounts, publishing listings, certification decisions, licensing)
    and tenant-facing marketplace browsing/installation.
  * **Third-party developers** — a `DeveloperApiKey` presented via the
    `X-Infinity-Developer-Key` header, authenticated through
    `infinity_developer_service.authenticate_api_key` (the same
    hash-only pattern `nexus_credential_service.py` already established).
    Used only for `/developer-portal/me`, the one endpoint a developer
    calls about themselves — everything else that manages a developer
    account is intentionally admin-gated, matching the brief's "trusted
    third parties" framing rather than open self-service.

  * GET  /developer-portal/api-explorer, /rate-limits, /tutorials,
    GET  /developer-portal/me                                            — Section 1
  * POST /developer-accounts, GET /developer-accounts,
    GET  /developer-accounts/{id}, PATCH /developer-accounts/{id}/status,
    POST /developer-accounts/{id}/api-keys,
    GET  /developer-accounts/{id}/api-keys,
    POST /developer-accounts/{id}/api-keys/{key_id}/revoke              — Section 1 (Auth)
  * POST /plugins, GET /plugins, GET /plugins/{plugin_key},
    POST /plugins/{plugin_key}/extensions,
    POST /plugins/{plugin_key}/activate, POST /plugins/{plugin_key}/disable — Sections 3, 6
  * POST /marketplace/listings, GET /marketplace/listings,
    GET  /marketplace/listings/{id},
    POST /marketplace/listings/{id}/submit-for-review,
    POST /marketplace/listings/{id}/publish, /unpublish,
    POST /marketplace/installations, GET /marketplace/installations,
    POST /marketplace/installations/{id}/uninstall                       — Sections 4, 5
  * POST /certification/listings/{id}/start, /advance,
    GET  /certification/listings/{id}                                    — Section 7
  * GET  /billing/module-licenses, POST /billing/partner-licenses,
    GET  /billing/partner-licenses,
    POST /billing/partner-licenses/{id}/revoke,
    POST /billing/revenue-events,
    GET  /billing/revenue-events/listings/{id}/summary                   — Section 8
  * POST /sandbox/sessions, GET /sandbox/sessions,
    GET  /sandbox/sessions/{id}, POST /sandbox/sessions/{id}/terminate,
    POST /sandbox/sessions/expire-stale                                  — Section 9
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.services import (
    infinity_billing_service,
    infinity_certification_service,
    infinity_developer_portal_service,
    infinity_developer_service,
    infinity_extension_service,
    infinity_marketplace_service,
    infinity_sandbox_service,
)
from app.tenant_authz import require_tenant_roles

router = APIRouter(prefix="/api/infinity", tags=["infinity"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user: dict) -> str:
    return current_user["tenant_id"]


def _actor(current_user: dict) -> str:
    return current_user["user_email"]


def _audit(db: Session, tenant_id: str, actor: str, action_type: str, resource_type: str, resource_id: str, details: dict) -> None:
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=actor, actor_role="",
        action_type=action_type, resource_type=resource_type, resource_id=resource_id, details=details, compliance_flag=True,
    )


def require_developer_auth(request: Request, db: Session = Depends(get_db)) -> dict:
    """Third-party developer auth via API key — never a tenant bearer
    token, since a developer is not necessarily tenant staff."""
    api_key = request.headers.get("X-Infinity-Developer-Key", "")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-Infinity-Developer-Key header.")
    key_row = infinity_developer_service.authenticate_api_key(db, api_key)
    if key_row is None:
        raise HTTPException(status_code=401, detail="Invalid, revoked, or expired developer API key.")
    return {"developer_account_id": key_row.developer_account_id}


# ---------------------------------------------------------------------------
# Section 1 — Developer Portal
# ---------------------------------------------------------------------------


@router.get("/developer-portal/api-explorer")
def get_api_explorer():
    return {"endpoints": infinity_developer_portal_service.api_explorer_catalog()}


@router.get("/developer-portal/rate-limits")
def get_rate_limits():
    return infinity_developer_portal_service.rate_limit_policy()


@router.get("/developer-portal/tutorials")
def get_tutorials():
    return {"tutorials": infinity_developer_portal_service.tutorials()}


@router.get("/developer-portal/me")
def get_my_developer_portal(db: Session = Depends(get_db), dev_auth: dict = Depends(require_developer_auth)):
    return infinity_developer_portal_service.developer_portal_summary(db, dev_auth["developer_account_id"])


# ---------------------------------------------------------------------------
# Section 1 (Authentication) — Developer accounts & API keys
# ---------------------------------------------------------------------------


@router.post("/developer-accounts", status_code=201)
def post_developer_account(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_developer_service.create_developer_account(
            db, email=payload.get("email", ""), organization_name=payload.get("organization_name", ""),
            developer_type=payload.get("developer_type", ""), approved_by=actor,
            sandbox_only=bool(payload.get("sandbox_only", True)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.developer_account_created", "infinity_developer_accounts", str(result["id"]), {"email": result["email"]})
    return result


@router.get("/developer-accounts")
def get_developer_accounts(status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"accounts": infinity_developer_service.list_developer_accounts(db, status=status)}


@router.get("/developer-accounts/{developer_account_id}")
def get_developer_account(developer_account_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return infinity_developer_service.get_developer_account(db, developer_account_id)
    except infinity_developer_service.DeveloperAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/developer-accounts/{developer_account_id}/status")
def patch_developer_account_status(developer_account_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_developer_service.set_developer_account_status(db, developer_account_id, status=payload.get("status", ""))
    except infinity_developer_service.DeveloperAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.developer_account_status_changed", "infinity_developer_accounts", str(developer_account_id), {"status": result["status"]})
    return result


@router.post("/developer-accounts/{developer_account_id}/api-keys", status_code=201)
def post_developer_api_key(developer_account_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_developer_service.issue_api_key(
            db, developer_account_id, scopes=payload.get("scopes"), sandbox_only=bool(payload.get("sandbox_only", True)),
        )
    except infinity_developer_service.DeveloperAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.developer_api_key_issued", "infinity_developer_api_keys", str(result["id"]), {})
    return result


@router.get("/developer-accounts/{developer_account_id}/api-keys")
def get_developer_api_keys(developer_account_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"api_keys": infinity_developer_service.list_api_keys(db, developer_account_id)}


@router.post("/developer-accounts/{developer_account_id}/api-keys/{key_id}/revoke")
def post_revoke_developer_api_key(developer_account_id: int, key_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    result = infinity_developer_service.revoke_api_key(db, developer_account_id, key_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"API key {key_id} not found for developer account {developer_account_id}.")
    _audit(db, tenant_id, actor, "infinity.developer_api_key_revoked", "infinity_developer_api_keys", str(key_id), {})
    return result


# ---------------------------------------------------------------------------
# Sections 3, 6 — Plugin SDK & Extension Framework
# ---------------------------------------------------------------------------


@router.post("/plugins", status_code=201)
def post_plugin(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    result = infinity_extension_service.register_plugin(
        db, plugin_key=payload.get("plugin_key", ""), name=payload.get("name", ""), version=payload.get("version", "0.1.0"),
        developer_account_id=payload.get("developer_account_id"), marketplace_listing_id=payload.get("marketplace_listing_id"),
        registered_by=actor,
    )
    _audit(db, tenant_id, actor, "infinity.plugin_registered", "platform_plugins", result["plugin_key"], {})
    return result


@router.get("/plugins")
def get_plugins(status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    return {"plugins": infinity_extension_service.list_plugins(db, status=status)}


@router.get("/plugins/{plugin_key}")
def get_plugin(plugin_key: str, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return infinity_extension_service.get_plugin(db, plugin_key)
    except infinity_extension_service.PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plugins/{plugin_key}/extensions")
def post_plugin_extension(plugin_key: str, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return infinity_extension_service.register_extension(
            db, plugin_key, extension_type=payload.get("extension_type", ""), location=payload.get("location", ""),
            item=payload.get("item", {}),
        )
    except infinity_extension_service.PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (infinity_extension_service.InvalidExtensionTypeError, infinity_extension_service.InvalidExtensionLocationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/plugins/{plugin_key}/activate")
def post_activate_plugin(plugin_key: str, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return infinity_extension_service.activate_plugin(db, plugin_key)
    except infinity_extension_service.PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/plugins/{plugin_key}/disable")
def post_disable_plugin(plugin_key: str, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return infinity_extension_service.disable_plugin(db, plugin_key)
    except infinity_extension_service.PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Sections 4, 5 — AI Skills Marketplace & Application Marketplace
# ---------------------------------------------------------------------------


@router.post("/marketplace/listings", status_code=201)
def post_marketplace_listing(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_marketplace_service.create_listing(
            db, payload.get("developer_account_id"), listing_type=payload.get("listing_type", ""),
            name=payload.get("name", ""), category=payload.get("category", ""), description=payload.get("description", ""),
            pricing_model=payload.get("pricing_model", "free"), price_cents=payload.get("price_cents"),
            manifest=payload.get("manifest"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.marketplace_listing_created", "infinity_marketplace_listings", str(result["id"]), {"listing_type": result["listing_type"]})
    return result


@router.get("/marketplace/listings")
def get_marketplace_listings(
    listing_type: str = Query(""), category: str = Query(""), status: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db),
):
    return {"listings": infinity_marketplace_service.list_listings(db, listing_type=listing_type, category=category, status=status)}


@router.get("/marketplace/listings/{listing_id}")
def get_marketplace_listing(listing_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return infinity_marketplace_service.get_listing(db, listing_id)
    except infinity_marketplace_service.ListingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/marketplace/listings/{listing_id}/submit-for-review")
def post_submit_listing_for_review(listing_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return infinity_marketplace_service.submit_for_review(db, listing_id)
    except infinity_marketplace_service.ListingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/marketplace/listings/{listing_id}/publish")
def post_publish_listing(listing_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_marketplace_service.publish_listing(db, listing_id)
    except infinity_marketplace_service.ListingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except infinity_marketplace_service.ListingNotCertifiedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.marketplace_listing_published", "infinity_marketplace_listings", str(listing_id), {})
    return result


@router.post("/marketplace/listings/{listing_id}/unpublish")
def post_unpublish_listing(listing_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return infinity_marketplace_service.unpublish_listing(db, listing_id)
    except infinity_marketplace_service.ListingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/marketplace/installations", status_code=201)
def post_marketplace_installation(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_marketplace_service.install_listing(db, tenant_id, payload.get("listing_id"), installed_by=actor)
    except infinity_marketplace_service.ListingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.marketplace_listing_installed", "infinity_marketplace_installations", str(result["id"]), {"listing_id": result["listing_id"]})
    return result


@router.get("/marketplace/installations")
def get_marketplace_installations(status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return {"installations": infinity_marketplace_service.list_installations(db, tenant_id, status=status)}


@router.post("/marketplace/installations/{installation_id}/uninstall")
def post_uninstall(installation_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_marketplace_service.uninstall(db, tenant_id, installation_id)
    except infinity_marketplace_service.InstallationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.marketplace_listing_uninstalled", "infinity_marketplace_installations", str(installation_id), {})
    return result


# ---------------------------------------------------------------------------
# Section 7 — Certification Program
# ---------------------------------------------------------------------------


@router.post("/certification/listings/{listing_id}/start")
def post_start_certification(listing_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_certification_service.start_certification(db, listing_id)
    except infinity_marketplace_service.ListingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.certification_started", "infinity_marketplace_listings", str(listing_id), {})
    return result


@router.post("/certification/listings/{listing_id}/advance")
def post_advance_certification(listing_id: int, payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_certification_service.advance_certification(
            db, listing_id, decided_by=actor, decided_role=payload.get("decided_role", ""),
            decision=payload.get("decision", ""), notes=payload.get("notes", ""),
        )
    except infinity_marketplace_service.ListingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.certification_advanced", "infinity_marketplace_listings", str(listing_id), {"decision": payload.get("decision", "")})
    return result


@router.get("/certification/listings/{listing_id}")
def get_certification_status(listing_id: int, current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    try:
        return infinity_certification_service.get_certification_status(db, listing_id)
    except infinity_marketplace_service.ListingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 8 — Billing & Licensing
# ---------------------------------------------------------------------------


@router.get("/billing/module-licenses")
def get_module_licenses(current_user: dict = Depends(require_tenant_roles(*_ALL_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    return infinity_billing_service.module_licensing_summary(db, tenant_id)


@router.post("/billing/partner-licenses", status_code=201)
def post_partner_license(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_billing_service.create_partner_license(
            db, license_type=payload.get("license_type", ""), developer_account_id=payload.get("developer_account_id"),
            tenant_id=payload.get("tenant_id", ""), licensed_module_keys=payload.get("licensed_module_keys"),
            terms=payload.get("terms", ""), revenue_share_pct=payload.get("revenue_share_pct"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.partner_license_created", "infinity_partner_licenses", str(result["id"]), {"license_type": result["license_type"]})
    return result


@router.get("/billing/partner-licenses")
def get_partner_licenses(
    developer_account_id: int = Query(None), tenant_id_filter: str = Query(""), status: str = Query(""),
    current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db),
):
    return {"licenses": infinity_billing_service.list_partner_licenses(db, developer_account_id=developer_account_id, tenant_id=tenant_id_filter, status=status)}


@router.post("/billing/partner-licenses/{license_id}/revoke")
def post_revoke_partner_license(license_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    result = infinity_billing_service.revoke_partner_license(db, license_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Partner license {license_id} not found.")
    _audit(db, tenant_id, actor, "infinity.partner_license_revoked", "infinity_partner_licenses", str(license_id), {})
    return result


@router.post("/billing/revenue-events", status_code=201)
def post_revenue_event(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_billing_service.record_revenue_event(
            db, payload.get("listing_id"), tenant_id, event_type=payload.get("event_type", ""),
            gross_amount_cents=payload.get("gross_amount_cents", 0), developer_share_pct=payload.get("developer_share_pct"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.revenue_event_recorded", "infinity_marketplace_revenue_events", str(result["id"]), {"event_type": result["event_type"]})
    return result


@router.get("/billing/revenue-events/listings/{listing_id}/summary")
def get_revenue_summary(listing_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return infinity_billing_service.revenue_summary_for_listing(db, listing_id)


# ---------------------------------------------------------------------------
# Section 9 — Developer Sandbox
# ---------------------------------------------------------------------------


@router.post("/sandbox/sessions", status_code=201)
def post_sandbox_session(payload: dict, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_sandbox_service.create_sandbox_session(
            db, payload.get("developer_account_id"), purpose=payload.get("purpose", ""),
            listing_id=payload.get("listing_id"), lifetime_hours=payload.get("lifetime_hours", 24),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.sandbox_session_created", "infinity_developer_sandbox_sessions", str(result["id"]), {"purpose": result["purpose"]})
    return result


@router.get("/sandbox/sessions")
def get_sandbox_sessions(developer_account_id: int = Query(...), status: str = Query(""), current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"sessions": infinity_sandbox_service.list_sandbox_sessions(db, developer_account_id, status=status)}


@router.get("/sandbox/sessions/{session_id}")
def get_sandbox_session(session_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    try:
        return infinity_sandbox_service.get_sandbox_session(db, session_id)
    except infinity_sandbox_service.SandboxSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sandbox/sessions/{session_id}/terminate")
def post_terminate_sandbox_session(session_id: int, current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    tenant_id = _tenant(current_user)
    actor = _actor(current_user)
    try:
        result = infinity_sandbox_service.terminate_sandbox_session(db, session_id)
    except infinity_sandbox_service.SandboxSessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _audit(db, tenant_id, actor, "infinity.sandbox_session_terminated", "infinity_developer_sandbox_sessions", str(session_id), {})
    return result


@router.post("/sandbox/sessions/expire-stale")
def post_expire_stale_sandbox_sessions(current_user: dict = Depends(require_tenant_roles(*_LEADERSHIP_ROLES)), db: Session = Depends(get_db)):
    return {"expired": infinity_sandbox_service.expire_stale_sessions(db)}
