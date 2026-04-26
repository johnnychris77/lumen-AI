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

