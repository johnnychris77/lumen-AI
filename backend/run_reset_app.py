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

app.openapi_schema = None
