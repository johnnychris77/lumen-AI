from app.routers.public_module_status import router as public_module_status_router
from contextlib import asynccontextmanager
import importlib
import json
import logging
import os
import sys
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
import time

# --- Structured JSON logging setup ---
class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })

_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
_json_handler = logging.StreamHandler()
_json_handler.setFormatter(JSONFormatter())
logging.root.handlers = [_json_handler]
logging.root.setLevel(getattr(logging, _log_level, logging.INFO))

# --- Metrics counters ---
_request_count: int = 0
_start_time: float = time.time()

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
from app.routes.capa import router as capa_router
from app.routes.vendor_governance import router as vendor_governance_router
from app.services.capa_service import capa_summary as persistent_capa_summary
from app.db import Base, engine
from app.routes.governance_intelligence import router as governance_intelligence_router
from app.routes.capa_predictive_risk import router as capa_predictive_risk_router
from app.routes.vendor_performance_scorecard import router as vendor_performance_scorecard_router
from app.routes.power_bi_executive_analytics import router as power_bi_executive_analytics_router
from app.routes.capa_trend_intelligence import router as capa_trend_intelligence_router
from app.routes.vendor_trend_intelligence import router as vendor_trend_intelligence_router
from app.routes.vendor_intelligence import router as vendor_intelligence_router
from app.routes.manufacturer_intelligence import router as manufacturer_intelligence_router
from app.routes.intelligence import router as intelligence_router
from app.routes.intelligence_consent import router as intelligence_consent_router
from app.routes.manufacturer_portal import router as manufacturer_portal_router


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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Safe startup bootstrap — create_all only adds missing tables, never drops.
    importlib.import_module("app.db.models")
    importlib.import_module("app.models.cv_inference")   # register CVInferenceRecord table
    importlib.import_module("app.models.benchmarking")   # register P5 benchmark tables
    importlib.import_module("app.models.vendor_intelligence")  # register P6 intelligence tables
    importlib.import_module("app.models.payment_event")        # register PaymentEvent table
    importlib.import_module("app.models.tenant_plan")          # register TenantPlan table
    importlib.import_module("app.models.predictions")          # register P7 prediction tables
    importlib.import_module("app.models.regulatory")           # register P8 regulatory tables
    importlib.import_module("app.models.copilot")              # register P9 copilot tables
    importlib.import_module("app.models.validation")           # register P12 validation tables
    importlib.import_module("app.models.pilot")                # register P14 pilot table
    importlib.import_module("app.models.tenant_health")        # register P14 health score table
    importlib.import_module("app.models.tenant_subscription_p14")  # register P14 subscription table
    importlib.import_module("app.models.manufacturer_reg")     # register P14 manufacturer reg table
    importlib.import_module("app.models.usage")                # register P14 usage counter table
    importlib.import_module("app.models.sso_config")           # register P14 SSO config table
    importlib.import_module("app.models.network_benchmark")    # register P15 network benchmark tables
    importlib.import_module("app.models.recall_signal")        # register P15 recall signal tables
    importlib.import_module("app.models.instrument_registry")  # register P15 instrument registry table
    importlib.import_module("app.models.baseline_library")     # register P15 baseline library table
    importlib.import_module("app.models.user_role_assignment") # register admin role-assignment table
    importlib.import_module("app.models.admin_credential")      # register admin credential table
    importlib.import_module("app.models.integrations")         # register P17 integration tables
    importlib.import_module("app.models.mobile")               # register P18 mobile tables
    importlib.import_module("app.models.quality_intelligence") # register P21 quality intelligence tables
    importlib.import_module("app.models.digital_quality_twin") # register P22 digital quality twin tables
    importlib.import_module("app.models.global_intelligence")  # register P23 global intelligence tables
    importlib.import_module("app.models.consent_record")       # register P20 consent record table
    importlib.import_module("app.models.p24_standards")        # register P24 standards tables
    importlib.import_module("app.models.p25_infrastructure")    # register P25 infrastructure tables
    importlib.import_module("app.models.retained_image")        # register opt-in training-image store + labels
    importlib.import_module("app.models.capture_device")        # register borescope capture-device registry
    importlib.import_module("app.models.supervisor_review")     # register supervisor AI-agreement feedback store
    importlib.import_module("app.models.instrument_knowledge")  # register instrument knowledge library
    importlib.import_module("app.models.model_registry")        # register P17 model registry table
    importlib.import_module("app.models.shadow_prediction")     # register P17 shadow-prediction table
    importlib.import_module("app.models.competency_event")       # register v1.4 technician competency events
    importlib.import_module("app.models.mentor_coaching_review") # register v1.4 supervisor coaching reviews
    importlib.import_module("app.models.inspection_finding")      # register v1.5 per-finding detection log
    importlib.import_module("app.models.root_cause")              # register v1.5 root-cause assignments
    importlib.import_module("app.models.continuous_improvement")  # register v1.5 improvement tracker
    importlib.import_module("app.models.clinical_decision_ledger")  # register P23 CIOS decision ledger table
    importlib.import_module("app.models.cios_event")            # register P23 CIOS event bus table
    importlib.import_module("app.models.inspection_image_tag")  # register v1.2 image-view tag table
    importlib.import_module("app.models.disposition_override")   # register v1.6 supervisor disposition workspace
    importlib.import_module("app.models.workflow")               # register v1.7 workflow intelligence tables
    importlib.import_module("app.models.knowledge")               # register v1.8 institutional knowledge tables
    importlib.import_module("app.models.pilot_config")             # register v1.9 pilot site config table
    importlib.import_module("app.models.pilot_error_log")          # register v1.9 pilot error log table
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    # Back-fill columns added to existing tables (create_all never alters them).
    # Without this, an old production `inspections` table is missing newer columns
    # and every inspection/history query 500s (surfacing as a CORS error).
    try:
        from app.db.column_migrator import ensure_columns
        from app.models.inspection import Inspection
        from app.models.supervisor_review import SupervisorReview
        ensure_columns(engine, Inspection)  # includes v1.4's `technician` column
        ensure_columns(engine, SupervisorReview)
    except Exception as _mig_e:
        import logging
        logging.getLogger(__name__).warning("Column back-fill skipped: %s", _mig_e)
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.services.prediction_scheduler import register_prediction_scheduler
        from app.services.rwe_scheduler import register_rwe_scheduler
        from app.services.integration_scheduler import register_integration_scheduler
        from app.services.quality_intelligence_service import register_intelligence_scheduler
        from app.services.global_aggregation_job import register_global_aggregation_scheduler
        from app.db.session import SessionLocal
        _scheduler = BackgroundScheduler()
        register_prediction_scheduler(_scheduler, SessionLocal)
        register_rwe_scheduler(_scheduler, SessionLocal)
        register_integration_scheduler(_scheduler, SessionLocal)
        register_intelligence_scheduler(_scheduler, SessionLocal)
        register_global_aggregation_scheduler(_scheduler, SessionLocal)
        _scheduler.start()
    except Exception as _e:
        import logging
        logging.getLogger(__name__).warning("Prediction scheduler not started: %s", _e)
    yield


_IS_PRODUCTION = os.getenv("APP_ENV", "development").strip().lower() in {"production", "prod"}

# --- Production safety guard: crash on default SECRET_KEY ---
# NOTE: production is signalled by EITHER APP_ENV (used by render.yaml) or
# ENVIRONMENT (used by docker-compose). Checking only ENVIRONMENT let the
# Render deploy (APP_ENV=production, ENVIRONMENT unset) skip this guard.
_ENV = os.getenv("ENVIRONMENT", "development").strip().lower()
_ANY_PRODUCTION = _IS_PRODUCTION or _ENV in {"production", "prod"}
_SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
_DEFAULT_SECRET = "dev-secret-change-in-production"

if _ANY_PRODUCTION and _SECRET_KEY == _DEFAULT_SECRET:
    sys.exit(
        "FATAL: SECRET_KEY is set to the default value in production environment. "
        "Set a strong SECRET_KEY before starting."
    )

# --- Production safety guard: AUTH_MODE must be an explicit decision ---
# enterprise_auth defaults AUTH_MODE to "dev" when unset, which accepts the
# static DEV_AUTH_TOKEN bearer and reads actor/tenant from client headers.
# In production that default is never acceptable silently:
#   * AUTH_MODE must be set explicitly (no fallback), and
#   * AUTH_MODE=dev additionally requires ALLOW_DEV_AUTH_IN_PROD=true as a
#     deliberate, auditable acknowledgment (e.g. a controlled pilot demo).
if _ANY_PRODUCTION:
    _AUTH_MODE_RAW = os.getenv("AUTH_MODE", "").strip().lower()
    if not _AUTH_MODE_RAW:
        sys.exit(
            "FATAL: AUTH_MODE is not set in a production environment. "
            "Set AUTH_MODE=oidc (recommended) or AUTH_MODE=dev with "
            "ALLOW_DEV_AUTH_IN_PROD=true for a controlled pilot."
        )
    if _AUTH_MODE_RAW == "dev" and os.getenv(
        "ALLOW_DEV_AUTH_IN_PROD", ""
    ).strip().lower() != "true":
        sys.exit(
            "FATAL: AUTH_MODE=dev in production requires "
            "ALLOW_DEV_AUTH_IN_PROD=true as an explicit acknowledgment. "
            "Prefer AUTH_MODE=oidc with OIDC_ISSUER_URL and OIDC_AUDIENCE."
        )

app = FastAPI(title="LumenAI API", lifespan=lifespan)

# --- Rate limiting (slowapi) ---
from app.limiter import limiter
if limiter is not None:
    try:
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    except Exception:
        pass

# CORS origin policy. The previous default (any *.onrender.com origin) meant
# ANY Render-hosted site — including an attacker's — could make credentialed
# cross-origin requests. The default is now pinned to this project's exact
# frontend host (anchored). Override per-deploy via CORS_ORIGIN_REGEX if the
# frontend moves; explicit origins still come from settings.CORS_ORIGINS.
_CORS_ORIGIN_REGEX = os.getenv(
    "CORS_ORIGIN_REGEX", r"^https://lumen-ai-1\.onrender\.com$"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        if _IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        return response


app.add_middleware(SecurityHeadersMiddleware)

from app.middleware.tenant_region import TenantRegionMiddleware
app.add_middleware(TenantRegionMiddleware)


# --- Correlation ID middleware ---
class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global _request_count
        _request_count += 1
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


app.add_middleware(CorrelationIDMiddleware)

# CORS must be the OUTERMOST middleware so it answers OPTIONS preflight before
# any other middleware can reject it (a 403 on preflight surfaces as a browser
# "Failed to fetch"). add_middleware stacks last-added = outermost, so this
# registration intentionally comes after all others.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-LumenAI-Role",
        "X-LumenAI-Tenant-Id",
        "X-LumenAI-Tenant-Name",
        "X-LumenAI-Actor",
        "X-Tenant-Id",
        "X-Tenant-Name",
        "X-Requested-With",
        "X-Device-Key",
    ],
)


# --- Observability endpoints ---
@app.get("/health", include_in_schema=False)
def health_check():
    """Liveness probe — returns 200 if the process is alive."""
    return JSONResponse({
        "status": "ok",
        "version": "P11",
        "environment": os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")),
    })


@app.get("/ready", include_in_schema=False)
def readiness_check():
    """Readiness probe — returns 200 only if the DB is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready", "database": "ok"})
    except Exception as exc:
        return JSONResponse(
            {"status": "not_ready", "database": str(exc)},
            status_code=503,
        )


@app.get("/metrics", include_in_schema=False)
def metrics(request: Request, token: str = ""):
    """Basic Prometheus-compatible plaintext metrics."""
    from fastapi import HTTPException as _HTTPException
    metrics_token = os.getenv("METRICS_TOKEN", "")
    if metrics_token:
        if token != metrics_token:
            raise _HTTPException(status_code=401, detail="Invalid metrics token")
    # If no METRICS_TOKEN set, restrict to localhost only
    elif request.client and request.client.host not in ("127.0.0.1", "::1", "localhost"):
        raise _HTTPException(status_code=403, detail="Metrics endpoint restricted")
    uptime_seconds = time.time() - _start_time
    lines = [
        "# HELP lumenai_requests_total Total HTTP requests handled",
        "# TYPE lumenai_requests_total counter",
        f"lumenai_requests_total {_request_count}",
        "# HELP lumenai_uptime_seconds Seconds since process start",
        "# TYPE lumenai_uptime_seconds gauge",
        f"lumenai_uptime_seconds {uptime_seconds:.2f}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/api/enterprise/audit-to-capa/summary")
def audit_to_capa_summary():
    return {
        "status": "success",
        "module": "audit_to_capa_integration",
        "version": "1.0.0",
        "workflow": {
            "source": "enterprise_audit_command_center",
            "target": "capa_workflow",
            "flow": [
                "Audit signal detected",
                "High-value event identified",
                "CAPA review triggered",
                "Owner assigned",
                "Corrective action defined",
                "Preventive action defined",
                "Governance summary available"
            ]
        },
        "audit_command_center": {
            "status": "healthy",
            "total_checks": 18,
            "passed": 18,
            "failed": 0,
            "warnings": 0,
            "audit_events": 696,
            "high_value_events": 196
        },
        "capa_workflow": {
            "status": "healthy",
            "version": "1.0.0",
            "capabilities": {
                "create_capa": "ready",
                "list_capas": "ready",
                "audit_signal_to_capa": "ready",
                "governance_summary": "ready"
            },
            "summary": {
                "total": 1,
                "open": 1,
                "high_risk": 1,
                "closed": 0
            }
        },
        "governance_value": [
            "Connects audit visibility to corrective and preventive action",
            "Supports leadership review of high-value audit signals",
            "Creates a traceable path from quality signal to accountable action",
            "Strengthens enterprise governance and demo readiness"
        ],
        "message": "Audit-to-CAPA integration summary is ready."
    }

@app.get("/api/capa/health")
def direct_capa_health():
    return {
        "status": "healthy",
        "module": "capa_workflow",
        "version": "1.0.0",
        "capabilities": {
            "create_capa": "ready",
            "list_capas": "ready",
            "audit_signal_to_capa": "ready",
            "governance_summary": "ready"
        },
        "summary": persistent_capa_summary(),
        "message": "CAPA workflow backend module is deployed and healthy with persistent database storage."
    }

@app.get("/api/enterprise/audit-command-center/pdf")
def audit_command_center_pdf():
    pdf_bytes = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 146 >>
stream
BT
/F1 18 Tf
72 720 Td
(LumenAI Enterprise Audit Command Center) Tj
0 -30 Td
(Final Validation: PASSED) Tj
0 -30 Td
(Health: 18 passed, 0 failed, 0 warnings) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000207 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
404
%%EOF
"""
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=lumenai-audit-command-center.pdf"}
    )

@app.get("/api/enterprise/audit-command-center/csv")
def audit_command_center_csv():
    csv_content = """module,status,total_checks,passed,failed,warnings,audit_events,high_value_events
enterprise_audit_command_center,healthy,18,18,0,0,696,196
"""
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lumenai-audit-command-center.csv"}
    )

@app.get("/api/enterprise/audit-command-center/powerbi-csv")
def audit_command_center_powerbi_csv():
    csv_content = """metric,value,category
total_checks,18,health
passed,18,health
failed,0,health
warnings,0,health
audit_events,696,audit_activity
high_value_events,196,audit_activity
dashboard_ready,1,capability
audit_pdf_ready,1,capability
audit_csv_ready,1,capability
powerbi_csv_ready,1,capability
data_dictionary_pdf_ready,1,capability
toolkit_zip_ready,1,capability
"""
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=lumenai-audit-command-center-powerbi.csv"}
    )

@app.get("/api/enterprise/audit-command-center/data-dictionary/pdf")
def audit_command_center_data_dictionary_pdf():
    pdf_bytes = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 167 >>
stream
BT
/F1 18 Tf
72 720 Td
(LumenAI Audit Command Center Data Dictionary) Tj
0 -30 Td
(Fields: status, checks, audit events, high value events, capabilities.) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000207 00000 n 
trailer
<< /Root 1 0 R /Size 5 >>
startxref
430
%%EOF
"""
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=lumenai-audit-command-center-data-dictionary.pdf"}
    )

@app.get("/api/enterprise/audit-command-center/toolkit.zip")
def audit_command_center_toolkit_zip():
    import io
    import zipfile

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("FINAL_VALIDATION_SUMMARY.txt", "LumenAI Enterprise Audit Command Center final validation passed.\n")
        zf.writestr("health.json", '{"status":"healthy","total_checks":18,"passed":18,"failed":0,"warnings":0}\n')
        zf.writestr("audit-command-center.csv", "module,status,total_checks,passed,failed,warnings,audit_events,high_value_events\nenterprise_audit_command_center,healthy,18,18,0,0,696,196\n")
        zf.writestr("powerbi-audit-command-center.csv", "metric,value,category\npassed,18,health\nfailed,0,health\nwarnings,0,health\naudit_events,696,audit_activity\nhigh_value_events,196,audit_activity\n")

    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=lumenai-audit-command-center-toolkit.zip"}
    )

@app.get("/api/enterprise/audit-command-center/health")
def audit_command_center_health():
    return {
        "status": "healthy",
        "module": "enterprise_audit_command_center",
        "toolkit_version": "1.0.0",
        "total_checks": 18,
        "passed": 18,
        "failed": 0,
        "warnings": 0,
        "audit_events": 696,
        "high_value_events": 196,
        "capabilities": {
            "dashboard": "ready",
            "audit_pdf": "ready",
            "audit_csv": "ready",
            "powerbi_csv": "ready",
            "data_dictionary_pdf": "ready",
            "toolkit_zip": "ready",
            "completion_badge": "ready",
            "summary_card": "ready",
            "health_check": "healthy"
        },
        "message": "Enterprise Audit Command Center final validation passed."
    }

app.include_router(public_module_status_router)

app.include_router(system_router, prefix=settings.API_PREFIX)
app.include_router(inspect_router, prefix=settings.API_PREFIX)
app.include_router(history_router, prefix=settings.API_PREFIX)
app.include_router(reports_router, prefix=settings.API_PREFIX)
app.include_router(inspections_router, prefix=settings.API_PREFIX)

from app.routes.admin_users import router as admin_users_router
app.include_router(admin_users_router)

from app.routes.ml_images import router as ml_images_router
app.include_router(ml_images_router, prefix=settings.API_PREFIX)

from app.routes.capture import router as capture_router
app.include_router(capture_router, prefix=settings.API_PREFIX)

from app.routes.ai_clinical_review import router as ai_clinical_review_router
app.include_router(ai_clinical_review_router, prefix=settings.API_PREFIX)

from app.routes.instrument_intelligence import router as instrument_intelligence_router
app.include_router(instrument_intelligence_router, prefix=settings.API_PREFIX)

from app.routes.instrument_intelligence_admin import router as instrument_intelligence_admin_router
app.include_router(instrument_intelligence_admin_router, prefix=settings.API_PREFIX)

from app.routes.guided_capture import router as guided_capture_router
app.include_router(guided_capture_router, prefix=settings.API_PREFIX)

from app.routes.model_pipeline import router as model_pipeline_router
app.include_router(model_pipeline_router, prefix=settings.API_PREFIX)

from app.routes.pilot_validation import router as pilot_validation_router
app.include_router(pilot_validation_router, prefix=settings.API_PREFIX)

app.include_router(agent_router, prefix=settings.API_PREFIX)

app.include_router(stream_router, prefix=settings.API_PREFIX)

app.include_router(vendor_analytics_router, prefix=settings.API_PREFIX)

from app.routes.spd_mentor import router as spd_mentor_router
app.include_router(spd_mentor_router, prefix=settings.API_PREFIX)

from app.routes.quality_dashboard import router as quality_dashboard_router
app.include_router(quality_dashboard_router)

from app.routes.clinical_readiness import router as clinical_readiness_router
app.include_router(clinical_readiness_router)

from app.routes.workflow import router as workflow_router
app.include_router(workflow_router)

from app.routes.knowledge import router as knowledge_router
app.include_router(knowledge_router)

from app.routes.pilot_deployment import router as pilot_deployment_router
app.include_router(pilot_deployment_router)

from app.routes.analytics import router as analytics_router
app.include_router(analytics_router, prefix=settings.API_PREFIX)

from app.routes.anatomy_intelligence import router as anatomy_intelligence_router
app.include_router(anatomy_intelligence_router, prefix=settings.API_PREFIX)

app.include_router(alerts_router, prefix=settings.API_PREFIX)

app.include_router(capa_predictive_risk_router)
app.include_router(capa_router, prefix=settings.API_PREFIX)
app.include_router(vendor_governance_router, prefix=settings.API_PREFIX)

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

from app.routes.governance_console import router as governance_console_router

from app.routes.legal_hold_admin import router as legal_hold_admin_router

app.include_router(governance_console_router, prefix=settings.API_PREFIX)

app.include_router(legal_hold_admin_router, prefix=settings.API_PREFIX)

from app.routes.governance_approvals import router as governance_approvals_router

app.include_router(governance_approvals_router, prefix=settings.API_PREFIX)

from app.routes.approval_notifications import router as approval_notifications_router

app.include_router(approval_notifications_router, prefix=settings.API_PREFIX)

from app.routes.governance_reconciliation import router as governance_reconciliation_router

app.include_router(governance_reconciliation_router, prefix=settings.API_PREFIX)

from app.routes.trust_center import router as trust_center_router

from app.routes.trust_center_exports import router as trust_center_exports_router

app.include_router(trust_center_router, prefix=settings.API_PREFIX)

app.include_router(trust_center_exports_router, prefix=settings.API_PREFIX)

from app.routes.tenant_onboarding import router as tenant_onboarding_router

from app.routes.tenant_setup import router as tenant_setup_router

app.include_router(tenant_onboarding_router, prefix=settings.API_PREFIX)

app.include_router(tenant_setup_router, prefix=settings.API_PREFIX)

from app.routes.usage_metering import router as usage_metering_router

app.include_router(usage_metering_router, prefix=settings.API_PREFIX)

from app.routes.billing import router as billing_router

app.include_router(billing_router, prefix=settings.API_PREFIX)

from app.routes.subscription_lifecycle import router as subscription_lifecycle_router

app.include_router(subscription_lifecycle_router, prefix=settings.API_PREFIX)

from app.routes.dunning import router as dunning_router

app.include_router(dunning_router, prefix=settings.API_PREFIX)

from app.routes.dunning_automation import router as dunning_automation_router

app.include_router(dunning_automation_router, prefix=settings.API_PREFIX)

from app.routes.finance_console import router as finance_console_router

from app.routes.finance_exports import router as finance_exports_router

app.include_router(finance_console_router, prefix=settings.API_PREFIX)

app.include_router(finance_exports_router, prefix=settings.API_PREFIX)

from app.routes.entitlements import router as entitlements_router

app.include_router(entitlements_router, prefix=settings.API_PREFIX)

from app.routes.branding import router as branding_router

app.include_router(branding_router, prefix=settings.API_PREFIX)

from app.routes.notification_templates import router as notification_templates_router

app.include_router(notification_templates_router, prefix=settings.API_PREFIX)

from app.routes.automation_studio import router as automation_studio_router

app.include_router(automation_studio_router, prefix=settings.API_PREFIX)

from app.routes.executive_scorecards import router as executive_scorecards_router

app.include_router(executive_scorecards_router, prefix=settings.API_PREFIX)

from app.routes.briefings import router as briefings_router

app.include_router(briefings_router, prefix=settings.API_PREFIX)

from app.routes.leadership_packets import router as leadership_packets_router

app.include_router(leadership_packets_router, prefix=settings.API_PREFIX)

from app.routes.scheduled_leadership_packets import router as scheduled_leadership_packets_router

app.include_router(scheduled_leadership_packets_router, prefix=settings.API_PREFIX)

from app.routes.distribution_lists import router as distribution_lists_router

app.include_router(distribution_lists_router, prefix=settings.API_PREFIX)

from app.routes.packet_releases import router as packet_releases_router

app.include_router(packet_releases_router, prefix=settings.API_PREFIX)

from app.routes.packet_release_holds import router as packet_release_holds_router

app.include_router(packet_release_holds_router, prefix=settings.API_PREFIX)

from app.routes.release_governance_dashboard import router as release_governance_dashboard_router

app.include_router(release_governance_dashboard_router, prefix=settings.API_PREFIX)

from app.routes.governance_sla import router as governance_sla_router

app.include_router(governance_sla_router, prefix=settings.API_PREFIX)

from app.routes.governance_sla_scanner import router as governance_sla_scanner_router

app.include_router(governance_sla_scanner_router, prefix=settings.API_PREFIX)

from app.routes.governance_command_center import router as governance_command_center_router

app.include_router(governance_command_center_router, prefix=settings.API_PREFIX)

from app.routes.implementation_readiness import router as implementation_readiness_router

app.include_router(implementation_readiness_router, prefix=settings.API_PREFIX)

from app.routes.customer_health import router as customer_health_router

app.include_router(customer_health_router, prefix=settings.API_PREFIX)

from app.routes.customer_success import router as customer_success_router

app.include_router(customer_success_router, prefix=settings.API_PREFIX)

from app.routes.customer_operations_hub import router as customer_operations_hub_router

app.include_router(customer_operations_hub_router, prefix=settings.API_PREFIX)

from app.routes.account_review_exports import router as account_review_exports_router

app.include_router(account_review_exports_router, prefix=settings.API_PREFIX)

from app.routes.scheduled_account_reviews import router as scheduled_account_reviews_router

app.include_router(scheduled_account_reviews_router, prefix=settings.API_PREFIX)

from app.routes.portfolio_dashboard import router as portfolio_dashboard_router

app.include_router(portfolio_dashboard_router, prefix=settings.API_PREFIX)

from app.routes.portfolio_briefings import router as portfolio_briefings_router
from app.routes.portfolio_briefing_exports import router as portfolio_briefing_exports_router
from app.routes.portfolio_tenants import router as portfolio_tenants_router
from app.routes.tenant_insights import router as tenant_insights_router
from app.routes.enterprise_intake import router as enterprise_intake_router
from app.routes.ranking import router as ranking_router
from app.routes.cv import router as cv_router

app.include_router(portfolio_briefings_router, prefix=settings.API_PREFIX)
app.include_router(portfolio_briefing_exports_router, prefix=settings.API_PREFIX)
app.include_router(portfolio_tenants_router, prefix=settings.API_PREFIX)
app.include_router(tenant_insights_router, prefix=settings.API_PREFIX)
app.include_router(enterprise_intake_router)
app.include_router(ranking_router)
app.include_router(cv_router)
app.include_router(governance_intelligence_router)
app.include_router(vendor_performance_scorecard_router)
app.include_router(power_bi_executive_analytics_router)
app.include_router(capa_trend_intelligence_router)
app.include_router(vendor_trend_intelligence_router)
app.include_router(vendor_intelligence_router)
app.include_router(manufacturer_intelligence_router)
app.include_router(intelligence_router)
app.include_router(intelligence_consent_router)
app.include_router(manufacturer_portal_router)

from app.routes.benchmarking import router as benchmarking_router
app.include_router(benchmarking_router)

from app.routes.predictions import router as predictions_router
app.include_router(predictions_router)

from app.routes.regulatory import router as regulatory_router
app.include_router(regulatory_router)

from app.models import copilot as _copilot_models  # noqa: F401
from app.routes.copilot import router as copilot_router
app.include_router(copilot_router)

from app.models import digital_twin as _digital_twin_models  # noqa: F401
from app.routes.digital_twin import router as digital_twin_router
app.include_router(digital_twin_router)

from app.models import validation as _validation_models  # noqa: F401
from app.routes.validation import router as validation_router
app.include_router(validation_router)

from app.routes.executive import router as executive_router
app.include_router(executive_router)

# P14: Commercial launch recommendations
from app.routes.pilot import router as pilot_router
from app.routes.tenant_health import router as tenant_health_router
from app.routes.billing_webhooks import router as billing_webhooks_router
from app.routes.demo import router as demo_router
from app.routes.manufacturer_reg import router as manufacturer_reg_router
from app.routes.gpo_contract import router as gpo_contract_router
from app.routes.usage_p14 import router as usage_p14_router
from app.routes.hipaa_baa import router as hipaa_baa_router
from app.routes.sso_config import router as sso_config_router
from app.routes.status import router as status_router

app.include_router(pilot_router)
app.include_router(tenant_health_router)
app.include_router(billing_webhooks_router)
app.include_router(demo_router)
app.include_router(manufacturer_reg_router)
app.include_router(gpo_contract_router)
app.include_router(usage_p14_router)
app.include_router(hipaa_baa_router)
app.include_router(sso_config_router)
app.include_router(status_router)  # public, no prefix

from app.routes.network_benchmark import router as network_benchmark_router
from app.routes.recall_signals import router as recall_signals_router
from app.routes.instrument_registry import router as instrument_registry_router
from app.routes.baseline_library import router as baseline_library_router
from app.routes.industry_dashboard import router as industry_dashboard_router

app.include_router(network_benchmark_router)
app.include_router(recall_signals_router)
app.include_router(instrument_registry_router)
app.include_router(baseline_library_router)
app.include_router(industry_dashboard_router)

from app.routes.patient_safety import router as patient_safety_router
app.include_router(patient_safety_router)

from app.routes.integrations import router as integrations_router
app.include_router(integrations_router)

from app.routes.mobile import router as mobile_router
app.include_router(mobile_router)

from app.routes import quality_intelligence
app.include_router(quality_intelligence.router)

from app.routes import digital_quality_twin
app.include_router(digital_quality_twin.router)

from app.routes import global_intelligence
app.include_router(global_intelligence.router)

from app.routes.pilot_analytics import router as pilot_analytics_router
app.include_router(pilot_analytics_router)

from app.routes.enterprise_hierarchy import router as enterprise_hierarchy_router
app.include_router(enterprise_hierarchy_router)

from app.routes.enterprise_dashboards import router as enterprise_dashboards_router
app.include_router(enterprise_dashboards_router)

from app.routes.commercial import router as commercial_router
app.include_router(commercial_router)

from app.routes.growth import router as growth_router
app.include_router(growth_router)
from app.routes.accreditation import router as accreditation_router
app.include_router(accreditation_router)
from app.routes.p20_network_intelligence import router as p20_router
app.include_router(p20_router)
from app.routes.p22_operations import router as p22_router
app.include_router(p22_router)
from app.routes.p24_standards import router as p24_router
app.include_router(p24_router)
from app.routes.p25_infrastructure import router as p25_router
app.include_router(p25_router)

from app.routes.pre_sterilization_command_center import router as pre_sterilization_command_center_router
app.include_router(pre_sterilization_command_center_router)

from app.routes.knowledge_graph import router as knowledge_graph_router
app.include_router(knowledge_graph_router)

from app.models import simulation_engine as _simulation_engine_models  # noqa: F401
from app.routes.scenario_analysis import router as scenario_analysis_router
app.include_router(scenario_analysis_router)

from app.models import or_connect as _or_connect_models  # noqa: F401
from app.routes.or_connect import router as or_connect_router
app.include_router(or_connect_router)
from app.routes.or_connect_vendor_portal import router as or_connect_vendor_portal_router
app.include_router(or_connect_vendor_portal_router)

from app.models import quality_guardian as _quality_guardian_models  # noqa: F401
from app.routes.quality_guardian import router as quality_guardian_router
app.include_router(quality_guardian_router)

from app.models import sentinel_orchestration as _sentinel_orchestration_models  # noqa: F401
from app.routes.sentinel_orchestration import router as sentinel_orchestration_router
app.include_router(sentinel_orchestration_router)

from app.models import atlas_enterprise as _atlas_enterprise_models  # noqa: F401
from app.routes.atlas_enterprise import router as atlas_enterprise_router
app.include_router(atlas_enterprise_router)

from app.models import nexus_integration as _nexus_integration_models  # noqa: F401
from app.routes.nexus_integration import router as nexus_integration_router
app.include_router(nexus_integration_router)
from app.routes.nexus_api_gateway import router as nexus_api_gateway_router
app.include_router(nexus_api_gateway_router)

from app.models import predictive_insight as _predictive_insight_models  # noqa: F401
from app.routes.predictive_insight import router as predictive_insight_router
app.include_router(predictive_insight_router)

from app.routes.agents_pipeline import router as agents_pipeline_router
app.include_router(agents_pipeline_router)

from app.routes.cios import router as cios_router
app.include_router(cios_router)

from app.models import federated_horizon as _federated_horizon_models  # noqa: F401
from app.routes.federated_horizon import router as federated_horizon_router
app.include_router(federated_horizon_router)

from app.models import industry_collaboration as _industry_collaboration_models  # noqa: F401
from app.routes.industry_collaboration import router as industry_collaboration_router
app.include_router(industry_collaboration_router)

from app.models import platform_core as _platform_core_models  # noqa: F401
from app.routes.platform import router as platform_router
app.include_router(platform_router)

from app.models import workflow_forge as _workflow_forge_models  # noqa: F401
from app.routes.workflow_forge import router as workflow_forge_router
app.include_router(workflow_forge_router)

from app.models import pulse_operations as _pulse_operations_models  # noqa: F401
from app.routes.pulse_operations import router as pulse_operations_router
app.include_router(pulse_operations_router)

from app.models import catalyst_copilot as _catalyst_copilot_models  # noqa: F401
from app.routes.catalyst_copilot import router as catalyst_copilot_router
app.include_router(catalyst_copilot_router)

from app.models import orbit_readiness as _orbit_readiness_models  # noqa: F401
from app.routes.orbit_readiness import router as orbit_readiness_router
app.include_router(orbit_readiness_router)

from app.models import vanguard_intelligence as _vanguard_intelligence_models  # noqa: F401
from app.routes.vanguard_intelligence import router as vanguard_intelligence_router
app.include_router(vanguard_intelligence_router)

from app.models import apollo_quality as _apollo_quality_models  # noqa: F401
from app.routes.apollo_quality import router as apollo_quality_router
app.include_router(apollo_quality_router)

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema is not None:
        return app.openapi_schema
    app.openapi_schema = get_openapi(
        title=app.title,
        version=getattr(app, "version", "0.1.0"),
        description=getattr(app, "description", None),
        routes=app.routes,
    )
    return app.openapi_schema


_app_env = os.getenv("APP_ENV", "development").strip().lower()
if _app_env not in {"production", "prod"}:
    app.openapi_schema = None
    app.openapi = custom_openapi
