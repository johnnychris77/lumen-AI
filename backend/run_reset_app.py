from app.main import app

API_PREFIX = "/api"


def _has_route(path: str) -> bool:
    return any(getattr(route, "path", None) == path for route in app.routes)


if not _has_route("/api/portfolio-briefings/generate"):
    from app.routes.portfolio_briefings import router as portfolio_briefings_router
    app.include_router(portfolio_briefings_router, prefix=API_PREFIX)

if not _has_route("/api/portfolio-briefings/{briefing_id}/exports"):
    from app.routes.portfolio_briefing_exports import router as portfolio_briefing_exports_router
    app.include_router(portfolio_briefing_exports_router, prefix=API_PREFIX)


if not _has_route("/api/portfolio-briefing-schedules"):
    from app.routes.portfolio_briefing_schedules import router as portfolio_briefing_schedules_router
    app.include_router(portfolio_briefing_schedules_router, prefix=API_PREFIX)


if not _has_route("/api/portfolio-briefing-scheduler/status"):
    from app.routes.portfolio_briefing_recurring_scheduler import router as portfolio_briefing_recurring_scheduler_router
    app.include_router(portfolio_briefing_recurring_scheduler_router, prefix=API_PREFIX)


if not _has_route("/api/portfolio-briefing-deliveries"):
    from app.routes.portfolio_briefing_deliveries import router as portfolio_briefing_deliveries_router
    app.include_router(portfolio_briefing_deliveries_router, prefix=API_PREFIX)


if not _has_route("/api/executive-briefing-dashboard/summary"):
    from app.routes.executive_briefing_dashboard import router as executive_briefing_dashboard_router
    app.include_router(executive_briefing_dashboard_router, prefix=API_PREFIX)


if not _has_route("/api/portfolio-tenants"):
    from app.routes.portfolio_tenants import router as portfolio_tenants_router
    app.include_router(portfolio_tenants_router, prefix=API_PREFIX)


if not _has_route("/api/tenant-insights/top-risks"):
    from app.routes.tenant_insights import router as tenant_insights_router
    app.include_router(tenant_insights_router, prefix=API_PREFIX)


if not _has_route("/api/tenant-remediations"):
    from app.routes.tenant_remediations import router as tenant_remediations_router
    app.include_router(tenant_remediations_router, prefix=API_PREFIX)


if not _has_route("/api/executive-escalations/run"):
    from app.routes.executive_escalations import router as executive_escalations_router
    app.include_router(executive_escalations_router, prefix=API_PREFIX)


if not _has_route("/api/governance-packets"):
    from app.routes.governance_packet_exports import router as governance_packet_exports_router
    app.include_router(governance_packet_exports_router, prefix=API_PREFIX)


if not _has_route("/api/executive-kpi-snapshots/capture"):
    from app.routes.executive_kpi_snapshots import router as executive_kpi_snapshots_router
    app.include_router(executive_kpi_snapshots_router, prefix=API_PREFIX)


if not _has_route("/api/executive-kpi-scheduler/status"):
    from app.routes.executive_kpi_scheduler import router as executive_kpi_scheduler_router
    app.include_router(executive_kpi_scheduler_router, prefix=API_PREFIX)


if not _has_route("/api/executive-decisions"):
    from app.routes.executive_decisions import router as executive_decisions_router
    app.include_router(executive_decisions_router, prefix=API_PREFIX)


if not _has_route("/api/enterprise-audit-events"):
    from app.routes.enterprise_audit import router as enterprise_audit_router
    app.include_router(enterprise_audit_router, prefix=API_PREFIX)


if not _has_route("/api/enterprise-access-control/decisions"):
    from app.routes.enterprise_access_control import router as enterprise_access_control_router
    app.include_router(enterprise_access_control_router, prefix=API_PREFIX)

app.openapi_schema = None


from app.portfolio_briefing_recurring_scheduler import (
    start_recurring_portfolio_briefing_scheduler,
    shutdown_recurring_portfolio_briefing_scheduler,
)


@app.on_event("startup")
def _start_portfolio_briefing_recurring_scheduler():
    start_recurring_portfolio_briefing_scheduler()


@app.on_event("shutdown")
def _stop_portfolio_briefing_recurring_scheduler():
    shutdown_recurring_portfolio_briefing_scheduler()



from app.executive_kpi_scheduler import (
    start_executive_kpi_scheduler,
    shutdown_executive_kpi_scheduler,
)


@app.on_event("startup")
def _start_executive_kpi_scheduler():
    start_executive_kpi_scheduler()


@app.on_event("shutdown")
def _stop_executive_kpi_scheduler():
    shutdown_executive_kpi_scheduler()



from starlette.requests import Request
from app.db import session as audit_db_session
from app.enterprise_audit import (
    create_audit_event,
    infer_action,
    infer_resource_type,
)


@app.middleware("http")
async def _enterprise_audit_middleware(request: Request, call_next):
    response = None
    status_code = 500
    path = request.url.path

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        try:
            if path.startswith("/api") and not any(skip in path for skip in ["/api/health"]):
                db = audit_db_session.SessionLocal()
                try:
                    authorization = request.headers.get("authorization", "")
                    actor = "dev-user" if "dev-token" in authorization else "unknown"
                    actor_role = "admin" if "dev-token" in authorization else "unknown"

                    create_audit_event(
                        db=db,
                        actor=actor,
                        actor_role=actor_role,
                        event_type="api_request",
                        resource_type=infer_resource_type(path),
                        action=infer_action(request.method, path),
                        method=request.method,
                        path=path,
                        status_code=status_code,
                        success=200 <= status_code < 400,
                        client_host=request.client.host if request.client else "",
                        user_agent=request.headers.get("user-agent", ""),
                        event_payload={
                            "query": str(request.url.query or ""),
                        },
                    )
                finally:
                    db.close()
        except Exception:
            pass



from starlette.responses import JSONResponse
from app.enterprise_access_control import (
    evaluate_access as enterprise_evaluate_access,
    infer_action as enterprise_infer_action,
    infer_actor_and_role as enterprise_infer_actor_and_role,
    infer_resource_type as enterprise_infer_resource_type,
    record_access_decision as enterprise_record_access_decision,
)


@app.middleware("http")
async def _enterprise_access_control_middleware(request, call_next):
    path = request.url.path

    if not path.startswith("/api") or path in {"/api/health"}:
        return await call_next(request)

    # Keep public API docs readable during local development.
    if path in {"/openapi.json", "/api/openapi.json"} or path.endswith("/view"):
        return await call_next(request)

    method = request.method.upper()
    headers = {k.lower(): v for k, v in request.headers.items()}

    actor, actor_role = enterprise_infer_actor_and_role(headers)
    resource_type = enterprise_infer_resource_type(path)
    action = enterprise_infer_action(method, path)

    decision = enterprise_evaluate_access(actor_role, resource_type, action)

    try:
        db = audit_db_session.SessionLocal()
        try:
            enterprise_record_access_decision(
                db=db,
                actor=actor,
                actor_role=actor_role,
                resource_type=resource_type,
                action=action,
                method=method,
                path=path,
                allowed=bool(decision["allowed"]),
                reason=str(decision["reason"]),
                policy=decision,
            )
        finally:
            db.close()
    except Exception:
        pass

    if not decision["allowed"]:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Access denied by enterprise policy",
                "policy": decision,
            },
        )

    return await call_next(request)

