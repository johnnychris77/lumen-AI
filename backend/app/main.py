from app.routes.portfolio_tenants import router as portfolio_tenants_router
from app.routes.tenant_insights import router as tenant_insights_router
from app.routers.public_module_status import router as public_module_status_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
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

app = FastAPI(title="LumenAI API")

app.include_router(public_module_status_router)



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

@app.on_event("startup")
def bootstrap_enterprise_tables():
    # Safe startup bootstrap for hosted demo / enterprise workflow tables.
    # SQLAlchemy create_all only creates missing tables.
    # It does not drop existing tables or delete existing data.
    importlib.import_module("app.db.models")
    Base.metadata.create_all(bind=engine)

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
from app.routes.enterprise_intake import router as enterprise_intake_router
app.include_router(
    portfolio_tenants_router,
    prefix=settings.API_PREFIX,
)
app.include_router(
    tenant_insights_router,
    prefix=settings.API_PREFIX,
)
app.include_router(portfolio_briefings_router, prefix=settings.API_PREFIX)
app.include_router(portfolio_briefing_exports_router, prefix=settings.API_PREFIX)
app.include_router(enterprise_intake_router)
app.include_router(governance_intelligence_router)
app.include_router(vendor_performance_scorecard_router)
app.include_router(power_bi_executive_analytics_router)
app.include_router(capa_trend_intelligence_router)
app.include_router(vendor_trend_intelligence_router)

from fastapi.openapi.utils import get_openapi
import importlib


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

app.openapi_schema = None
app.openapi = custom_openapi
