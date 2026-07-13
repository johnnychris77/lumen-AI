"""v3.1 — Project Atlas: Enterprise Intelligence & Multi-Site Operations routes.

Route: /atlas (frontend). API prefix: /api/atlas. Section 1 (Enterprise
Organization Model) is already served by the existing /api/enterprise
routes (`app/routes/enterprise_hierarchy.py`) — no new routes here for it.

  * GET /dashboard/{system_id}                                       — Section 2
  * GET /benchmarking/{system_id}                                    — Section 3
  * GET /watchlist/{system_id}, POST /watchlist/{system_id}/refresh,
    POST /watchlist/{system_id}/{entry_id}/resolve                   — Section 4
  * GET /facility-intelligence/{system_id}/{facility_id}             — Section 5
  * POST /knowledge/share, GET /knowledge/{system_id},
    GET /knowledge/{system_id}/{article_id},
    POST /knowledge/{system_id}/{article_id}/retract                — Section 6
  * GET /analytics/{system_id}/trend, GET /analytics/{system_id}/trend/all — Section 7
  * GET /alerts/{system_id}, POST /alerts/{system_id}/generate,
    POST /alerts/{system_id}/{alert_id}/acknowledge|resolve         — Section 8
  * POST /reports/{system_id}/generate, GET /reports/{system_id},
    GET /reports/{system_id}/{report_id},
    GET /reports/{system_id}/{report_id}.csv|.xlsx|.pdf             — Section 9
  * POST /roles/grant, GET /roles/{user_email},
    POST /roles/{assignment_id}/revoke, GET /roles/access-check      — Section 10
"""
from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.atlas_enterprise import ENTERPRISE_ROLES, ROLE_SCOPES, SCOPE_FACILITY, SCOPE_SYSTEM
from app.services import (
    atlas_alert_service,
    atlas_analytics_service,
    atlas_benchmarking_service,
    atlas_dashboard_service,
    atlas_knowledge_sharing_service,
    atlas_rbac_service,
    atlas_report_service,
    atlas_watchlist_service,
)
from app.services.atlas_knowledge_sharing_service import ArticleNotApprovedError, ArticleNotFoundError

router = APIRouter(prefix="/api/atlas", tags=["atlas"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


def _require_scope(scope_type: str, *roles: str):
    """Enforces that the caller holds a real EnterpriseRoleAssignment covering
    the system_id/facility_id in the request path — not just a matching role
    string. Without this, any authenticated user holding one of `roles` could
    request another organization's enterprise data by supplying its
    system_id/facility_id, since role checks alone say nothing about which
    organization the caller actually belongs to."""

    def _check(
        request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*roles)),
    ):
        path_key = "facility_id" if scope_type == SCOPE_FACILITY else "system_id"
        scope_id = request.path_params.get(path_key, "")
        actor = _actor(current_user)
        has_access = atlas_rbac_service.user_has_scope_access(db, actor, scope_type=scope_type, scope_id=scope_id)
        if not has_access and scope_type == SCOPE_FACILITY:
            # An unknown facility_id has no lineage to check against, so the
            # facility-scope lookup above can't resolve it -- fall back to the
            # system_id already present in this route's own path so a
            # not-yet-existent (or since-deleted) facility doesn't mask a real
            # system-level grant behind an opaque 403 (the route's own logic
            # still 404s for a genuinely unknown facility).
            path_system_id = request.path_params.get("system_id", "")
            has_access = bool(path_system_id) and atlas_rbac_service.user_has_scope_access(
                db, actor, scope_type=SCOPE_SYSTEM, scope_id=path_system_id,
            )
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"You do not have an enterprise role assignment covering this {scope_type} ('{scope_id}').",
            )
        return current_user

    return _check


require_system_access = _require_scope(SCOPE_SYSTEM, *_ALL_ROLES)
require_system_access_leadership = _require_scope(SCOPE_SYSTEM, *_LEADERSHIP_ROLES)
require_facility_access = _require_scope(SCOPE_FACILITY, *_ALL_ROLES)


# ---------------------------------------------------------------------------
# Section 2 — Enterprise Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard/{system_id}")
def get_enterprise_dashboard(
    system_id: str, db: Session = Depends(get_db), current_user=Depends(require_system_access),
):
    return atlas_dashboard_service.enterprise_dashboard(db, system_id)


# ---------------------------------------------------------------------------
# Section 3 — Cross-Facility Benchmarking
# ---------------------------------------------------------------------------


@router.get("/benchmarking/{system_id}")
def get_cross_facility_benchmark(
    system_id: str, db: Session = Depends(get_db), current_user=Depends(require_system_access),
):
    return atlas_benchmarking_service.cross_facility_benchmark(db, system_id)


# ---------------------------------------------------------------------------
# Section 4 — Enterprise Watchlists
# ---------------------------------------------------------------------------


@router.post("/watchlist/{system_id}/refresh")
def post_refresh_enterprise_watchlist(
    system_id: str, db: Session = Depends(get_db), current_user=Depends(require_system_access_leadership),
):
    return {"watchlist": atlas_watchlist_service.refresh_enterprise_watchlists(db, system_id)}


@router.get("/watchlist/{system_id}")
def get_enterprise_watchlist(
    system_id: str, entity_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_system_access),
):
    return {"watchlist": atlas_watchlist_service.list_active_watchlist(db, system_id, entity_type=entity_type)}


@router.post("/watchlist/{system_id}/{entry_id}/resolve")
def post_resolve_enterprise_watchlist_entry(
    system_id: str, entry_id: int, db: Session = Depends(get_db), current_user=Depends(require_system_access_leadership),
):
    result = atlas_watchlist_service.resolve_watchlist_entry(db, system_id, entry_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Watchlist entry {entry_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 5 — Facility Intelligence
# ---------------------------------------------------------------------------


@router.get("/facility-intelligence/{system_id}/{facility_id}")
def get_facility_intelligence(
    system_id: str, facility_id: str, db: Session = Depends(get_db), current_user=Depends(require_facility_access),
):
    result = atlas_dashboard_service.compute_facility_intelligence(db, system_id, facility_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Facility {facility_id} not found in system {system_id}.")
    return result


# ---------------------------------------------------------------------------
# Section 6 — Enterprise Knowledge Sharing
# ---------------------------------------------------------------------------


@router.post("/knowledge/share")
def post_share_knowledge_article(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    # system_id arrives in the JSON body here, not the URL path, so the
    # path-based require_system_access_leadership dependency can't see it —
    # check scope access explicitly instead.
    share_system_id = payload.get("system_id", "")
    if not atlas_rbac_service.user_has_scope_access(db, _actor(current_user), scope_type=SCOPE_SYSTEM, scope_id=share_system_id):
        raise HTTPException(
            status_code=403,
            detail=f"You do not have an enterprise role assignment covering this system ('{share_system_id}').",
        )
    tenant_id = _tenant(current_user, request)
    try:
        return atlas_knowledge_sharing_service.share_article(
            db, payload["system_id"], source_tenant_id=payload.get("source_tenant_id", tenant_id),
            source_article_id=payload["source_article_id"], owner=payload.get("owner", _actor(current_user)),
            approver=payload.get("approver", ""), sharing_scope=payload.get("sharing_scope", "system_wide"),
        )
    except (ArticleNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ArticleNotApprovedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/knowledge/{system_id}")
def get_shared_knowledge_articles(
    system_id: str, sharing_scope: str = Query(""), category: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_system_access),
):
    return {"articles": atlas_knowledge_sharing_service.list_shared_articles(db, system_id, sharing_scope=sharing_scope, category=category)}


@router.get("/knowledge/{system_id}/{article_id}")
def get_shared_knowledge_article(
    system_id: str, article_id: int, db: Session = Depends(get_db), current_user=Depends(require_system_access),
):
    result = atlas_knowledge_sharing_service.get_shared_article(db, system_id, article_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Shared article {article_id} not found.")
    return result


@router.post("/knowledge/{system_id}/{article_id}/retract")
def post_retract_shared_knowledge_article(
    system_id: str, article_id: int, db: Session = Depends(get_db), current_user=Depends(require_system_access_leadership),
):
    result = atlas_knowledge_sharing_service.retract_shared_article(db, system_id, article_id, retracted_by=_actor(current_user))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Shared article {article_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 7 — Enterprise Analytics
# ---------------------------------------------------------------------------


@router.get("/analytics/{system_id}/trend")
def get_enterprise_trend(
    system_id: str, metric: str = Query(...), granularity: str = Query("monthly"), db: Session = Depends(get_db),
    current_user=Depends(require_system_access),
):
    try:
        return atlas_analytics_service.enterprise_trend(db, system_id, metric=metric, granularity=granularity)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/analytics/{system_id}/trend/all")
def get_all_metrics_trend(
    system_id: str, granularity: str = Query("monthly"), db: Session = Depends(get_db),
    current_user=Depends(require_system_access),
):
    return atlas_analytics_service.all_metrics_trend(db, system_id, granularity=granularity)


# ---------------------------------------------------------------------------
# Section 8 — Enterprise Alerts
# ---------------------------------------------------------------------------


@router.post("/alerts/{system_id}/generate")
def post_generate_enterprise_alerts(
    system_id: str, db: Session = Depends(get_db), current_user=Depends(require_system_access_leadership),
):
    return {"alerts": atlas_alert_service.generate_enterprise_alerts(db, system_id)}


@router.get("/alerts/{system_id}")
def get_enterprise_alerts(
    system_id: str, severity: str = Query(""), unresolved_only: bool = Query(True), db: Session = Depends(get_db),
    current_user=Depends(require_system_access),
):
    return {"alerts": atlas_alert_service.list_alerts(db, system_id, severity=severity, unresolved_only=unresolved_only)}


@router.post("/alerts/{system_id}/{alert_id}/acknowledge")
def post_acknowledge_enterprise_alert(
    system_id: str, alert_id: int, db: Session = Depends(get_db), current_user=Depends(require_system_access),
):
    result = atlas_alert_service.acknowledge_alert(db, system_id, alert_id, acknowledged_by=_actor(current_user))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return result


@router.post("/alerts/{system_id}/{alert_id}/resolve")
def post_resolve_enterprise_alert(
    system_id: str, alert_id: int, db: Session = Depends(get_db), current_user=Depends(require_system_access_leadership),
):
    result = atlas_alert_service.resolve_alert(db, system_id, alert_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 9 — Executive Reports
# ---------------------------------------------------------------------------


@router.post("/reports/{system_id}/generate")
def post_generate_executive_report(
    system_id: str, payload: dict, db: Session = Depends(get_db), current_user=Depends(require_system_access_leadership),
):
    try:
        return atlas_report_service.generate_executive_report(
            db, system_id, audience=payload["audience"], cadence=payload["cadence"],
            market_id=payload.get("market_id", ""), facility_id=payload.get("facility_id", ""),
            generated_by=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/reports/{system_id}")
def get_executive_reports(
    system_id: str, audience: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_system_access),
):
    return {"reports": atlas_report_service.list_reports(db, system_id, audience=audience)}


def _load_report_or_404(db: Session, system_id: str, report_id: int) -> dict:
    result = atlas_report_service.get_report(db, system_id, report_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")
    return result


# NOTE: these dotted-suffix export routes must be registered before the plain
# GET /reports/{system_id}/{report_id} route below — FastAPI/Starlette match
# routes in registration order, and a request for ".../1.csv" would otherwise
# match the generic {report_id} route first (then fail int-conversion with a
# 422) rather than falling through to the more specific route.
@router.get("/reports/{system_id}/{report_id}.csv")
def get_executive_report_csv(
    system_id: str, report_id: int, db: Session = Depends(get_db), current_user=Depends(require_system_access),
):
    report = _load_report_or_404(db, system_id, report_id)
    content = atlas_report_service.build_report_csv_bytes(report)
    return StreamingResponse(
        BytesIO(content), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report['report_ref']}.csv"},
    )


@router.get("/reports/{system_id}/{report_id}.xlsx")
def get_executive_report_xlsx(
    system_id: str, report_id: int, db: Session = Depends(get_db), current_user=Depends(require_system_access),
):
    report = _load_report_or_404(db, system_id, report_id)
    content = atlas_report_service.build_report_xlsx_bytes(report)
    return StreamingResponse(
        BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={report['report_ref']}.xlsx"},
    )


@router.get("/reports/{system_id}/{report_id}.pdf")
def get_executive_report_pdf(
    system_id: str, report_id: int, db: Session = Depends(get_db), current_user=Depends(require_system_access),
):
    report = _load_report_or_404(db, system_id, report_id)
    content = atlas_report_service.build_report_pdf_bytes(report)
    return StreamingResponse(
        BytesIO(content), media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={report['report_ref']}.pdf"},
    )


@router.get("/reports/{system_id}/{report_id}")
def get_executive_report(
    system_id: str, report_id: int, db: Session = Depends(get_db), current_user=Depends(require_system_access),
):
    return _load_report_or_404(db, system_id, report_id)


# ---------------------------------------------------------------------------
# Section 10 — Governance / RBAC
# ---------------------------------------------------------------------------


@router.post("/roles/grant")
def post_grant_role(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    # `admin` acts as the bootstrap identity that can grant the very first
    # role assignment for a brand-new system (there would otherwise be no
    # way to create one). Every other leadership role must already hold a
    # real assignment covering the scope they're trying to grant into --
    # otherwise a leadership user from one organization could grant
    # themselves (or anyone else) a role scoped to a different organization
    # and use it to bypass the very access check this fix adds elsewhere.
    grant_scope_type = payload.get("scope_type", "")
    grant_scope_id = payload.get("scope_id", "")
    if current_user.role != "admin" and not atlas_rbac_service.user_has_scope_access(
        db, _actor(current_user), scope_type=grant_scope_type, scope_id=grant_scope_id,
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You do not have an enterprise role assignment covering this {grant_scope_type or 'scope'} ('{grant_scope_id}'), so you cannot grant roles there.",
        )
    try:
        result = atlas_rbac_service.grant_role(
            db, user_email=payload["user_email"], role=payload["role"], scope_type=payload["scope_type"],
            scope_id=payload["scope_id"], granted_by=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    tenant_id = _tenant(current_user, request)
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="atlas.role_granted", resource_type="enterprise_role_assignment", resource_id=str(result["id"]),
        details={"user_email": payload["user_email"], "role": payload["role"], "scope_type": payload["scope_type"], "scope_id": payload["scope_id"]},
    )
    return result


# NOTE: this static route must be registered before GET /roles/{user_email}
# below — otherwise a request for "/roles/access-check" would match the
# generic {user_email} route first (treating "access-check" as an email).
@router.get("/roles/access-check")
def get_access_check(
    user_email: str = Query(...), scope_type: str = Query(...), scope_id: str = Query(...),
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    if scope_type not in ROLE_SCOPES:
        raise HTTPException(status_code=422, detail=f"scope_type must be one of {ROLE_SCOPES}")
    has_access = atlas_rbac_service.user_has_scope_access(db, user_email, scope_type=scope_type, scope_id=scope_id)
    return {"user_email": user_email, "scope_type": scope_type, "scope_id": scope_id, "has_access": has_access, "valid_roles": ENTERPRISE_ROLES}


@router.get("/roles/{user_email}")
def get_roles_for_user(
    user_email: str, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return {"roles": atlas_rbac_service.list_roles_for_user(db, user_email)}


@router.post("/roles/{assignment_id}/revoke")
def post_revoke_role(
    assignment_id: int, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    result = atlas_rbac_service.revoke_role(db, assignment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Role assignment {assignment_id} not found.")
    return result
