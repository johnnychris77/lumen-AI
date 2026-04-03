from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import time

from app.core.settings import settings
from app.routes.system import router as system_router
from app.routes.inspect import router as inspect_router
from app.routes.history import router as history_router
from app.routes.reports import router as reports_router
from app.routes.inspections import router as inspections_router
from app.routes.agent import router as agent_router
from app.routes.qa_review import router as qa_review_router
from app.routes.review_analytics import router as review_analytics_router
from app.routes.model_performance import router as model_performance_router
from app.routes.stream import router as stream_router
from app.routes.vendor_analytics import router as vendor_analytics_router
from app.routes.alerts import router as alerts_router
from app.db import Base, engine

app = FastAPI(title="LumenAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def wait_for_db(max_attempts: int = 30, sleep_seconds: int = 2) -> None:
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"Database ready on attempt {attempt}")
            return
        except Exception as exc:
            last_error = exc
            print(f"Database not ready (attempt {attempt}/{max_attempts}): {exc}")
            time.sleep(sleep_seconds)
    raise RuntimeError(f"Database did not become ready: {last_error}")


@app.on_event("startup")
async def _startup() -> None:
    wait_for_db()
    Base.metadata.create_all(bind=engine)


app.include_router(system_router, prefix=settings.API_PREFIX)
app.include_router(inspect_router, prefix=settings.API_PREFIX)
app.include_router(history_router, prefix=settings.API_PREFIX)
app.include_router(reports_router, prefix=settings.API_PREFIX)
app.include_router(inspections_router, prefix=settings.API_PREFIX)

app.include_router(agent_router, prefix=settings.API_PREFIX)

app.include_router(stream_router, prefix=settings.API_PREFIX)

app.include_router(vendor_analytics_router, prefix=settings.API_PREFIX)

app.include_router(alerts_router, prefix=settings.API_PREFIX)

app.include_router(qa_review_router, prefix=settings.API_PREFIX)

app.include_router(review_analytics_router, prefix=settings.API_PREFIX)

app.include_router(model_performance_router, prefix=settings.API_PREFIX)


from app.routes.site_analytics import router as site_analytics_router
from app.routes.executive_digest import router as executive_digest_router
from app.routes.board_reporting import router as board_reporting_router
from app.routes.digest_scheduler import router as digest_scheduler_router

app.include_router(site_analytics_router, prefix=settings.API_PREFIX)

app.include_router(executive_digest_router, prefix=settings.API_PREFIX)

app.include_router(board_reporting_router, prefix=settings.API_PREFIX)

app.include_router(digest_scheduler_router, prefix=settings.API_PREFIX)
from app.routes.digest_delivery import router as digest_delivery_router
from app.services.digest_scheduler_service import start_digest_scheduler
from app.services.retention_scheduler_service import start_retention_scheduler
app.include_router(digest_delivery_router, prefix=settings.API_PREFIX)

from app.routes.digest_subscriptions import router as digest_subscriptions_router

app.include_router(digest_subscriptions_router, prefix=settings.API_PREFIX)

from app.routes.tenant_analytics import router as tenant_analytics_router

app.include_router(tenant_analytics_router, prefix=settings.API_PREFIX)

from app.routes.tenant_admin import router as tenant_admin_router

from app.routes.tenant_scoped_subscriptions import router as tenant_scoped_subscriptions_router

app.include_router(tenant_admin_router, prefix=settings.API_PREFIX)
app.include_router(tenant_scoped_subscriptions_router, prefix=settings.API_PREFIX)

from app.routes.audit_logs import router as audit_logs_router

app.include_router(audit_logs_router, prefix=settings.API_PREFIX)

from app.routes.compliance_exports import router as compliance_exports_router

app.include_router(compliance_exports_router, prefix=settings.API_PREFIX)

from app.routes.retention_admin import router as retention_admin_router

app.include_router(retention_admin_router, prefix=settings.API_PREFIX)

from app.routes.retention_enforcement import router as retention_enforcement_router

app.include_router(retention_enforcement_router, prefix=settings.API_PREFIX)

from app.routes.retention_scheduler import router as retention_scheduler_router

app.include_router(retention_scheduler_router, prefix=settings.API_PREFIX)
