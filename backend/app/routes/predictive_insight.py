"""v3.3 — Project Insight: Predictive Clinical Intelligence & Quality
Forecasting routes.

Route: /forecast (frontend). API prefix: /api/insight.

  * GET /intelligence                                              — Section 1
  * GET /quality-trends, POST /quality-trends/generate              — Section 3
  * GET /operational-forecasts, POST /operational-forecasts/generate — Section 5
  * GET /instrument-lifecycle, POST /instrument-lifecycle/generate   — Sections 2 & 6
  * GET /education-signals, POST /education-signals/generate         — Section 4
  * GET /recommendations, POST /recommendations/generate,
    POST /recommendations/{id}/action|dismiss                       — Section 8
  * POST /reports/generate, GET /reports, GET /reports/{id},
    GET /reports/{id}.csv|.xlsx|.pdf                                — Section 9
  * GET /dashboard                                                  — Section 7
"""
from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.services import (
    insight_education_forecast_service,
    insight_engine_service,
    insight_instrument_forecast_service,
    insight_operational_forecast_service,
    insight_quality_trend_service,
    insight_recommendation_service,
    insight_report_service,
)

router = APIRouter(prefix="/api/insight", tags=["insight"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


# ---------------------------------------------------------------------------
# Section 1 — Predictive Intelligence Engine
# ---------------------------------------------------------------------------


@router.get("/intelligence")
def get_predictive_intelligence(
    request: Request, horizon: str = Query("30_day"), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return insight_engine_service.generate_predictive_intelligence(db, tenant_id, horizon=horizon)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 3 — Quality Trend Forecasting
# ---------------------------------------------------------------------------


@router.post("/quality-trends/generate")
def post_generate_quality_trends(
    request: Request, horizon: str = Query("30_day"), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return {"forecasts": insight_quality_trend_service.generate_all_quality_trend_forecasts(db, tenant_id, horizon=horizon)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/quality-trends")
def get_quality_trends(
    request: Request, metric: str = Query(""), horizon: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"forecasts": insight_quality_trend_service.list_quality_trend_forecasts(db, tenant_id, metric=metric, horizon=horizon)}


# ---------------------------------------------------------------------------
# Section 5 — Operational Forecasting
# ---------------------------------------------------------------------------


@router.post("/operational-forecasts/generate")
def post_generate_operational_forecasts(
    request: Request, horizon: str = Query("30_day"), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return {"forecasts": insight_operational_forecast_service.generate_all_operational_forecasts(db, tenant_id, horizon=horizon)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/operational-forecasts")
def get_operational_forecasts(
    request: Request, forecast_type: str = Query(""), horizon: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"forecasts": insight_operational_forecast_service.list_operational_forecasts(db, tenant_id, forecast_type=forecast_type, horizon=horizon)}


# ---------------------------------------------------------------------------
# Sections 2 & 6 — Instrument Failure Forecasting & Predictive Digital Twin Analytics
# ---------------------------------------------------------------------------


@router.post("/instrument-lifecycle/generate")
def post_generate_instrument_lifecycle(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"forecasts": insight_instrument_forecast_service.generate_lifecycle_forecasts_for_tenant(db, tenant_id)}


@router.get("/instrument-lifecycle")
def get_instrument_lifecycle(
    request: Request, instrument_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"forecasts": insight_instrument_forecast_service.list_lifecycle_forecasts(db, tenant_id, instrument_type=instrument_type)}


# ---------------------------------------------------------------------------
# Section 4 — Predictive Education Engine
# ---------------------------------------------------------------------------


@router.post("/education-signals/generate")
def post_generate_education_signals(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return insight_education_forecast_service.generate_predictive_education_signals(db, tenant_id)


@router.get("/education-signals")
def get_education_signals(
    request: Request, signal_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"signals": insight_education_forecast_service.list_education_signals(db, tenant_id, signal_type=signal_type)}


# ---------------------------------------------------------------------------
# Section 8 — Predictive Recommendation Engine
# ---------------------------------------------------------------------------


@router.post("/recommendations/generate")
def post_generate_recommendations(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"recommendations": insight_recommendation_service.generate_recommendations(db, tenant_id)}


@router.get("/recommendations")
def get_recommendations(
    request: Request, status: str = Query(""), recommendation_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"recommendations": insight_recommendation_service.list_recommendations(db, tenant_id, status=status, recommendation_type=recommendation_type)}


@router.post("/recommendations/{recommendation_id}/action")
def post_action_recommendation(
    recommendation_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = insight_recommendation_service.action_recommendation(db, tenant_id, recommendation_id, actioned_by=_actor(current_user))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found.")
    return result


@router.post("/recommendations/{recommendation_id}/dismiss")
def post_dismiss_recommendation(
    recommendation_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = insight_recommendation_service.dismiss_recommendation(db, tenant_id, recommendation_id, actioned_by=_actor(current_user))
    if result is None:
        raise HTTPException(status_code=404, detail=f"Recommendation {recommendation_id} not found.")
    return result


# ---------------------------------------------------------------------------
# Section 9 — Executive Forecast Reports
# ---------------------------------------------------------------------------


@router.post("/reports/generate")
def post_generate_report(
    payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return insight_report_service.generate_executive_forecast_report(
            db, tenant_id, cadence=payload["cadence"], generated_by=_actor(current_user),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/reports")
def get_reports(
    request: Request, cadence: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"reports": insight_report_service.list_reports(db, tenant_id, cadence=cadence)}


def _load_report_or_404(db: Session, tenant_id: str, report_id: int) -> dict:
    result = insight_report_service.get_report(db, tenant_id, report_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found.")
    return result


# NOTE: these dotted-suffix export routes must be registered before the plain
# GET /reports/{report_id} route below — FastAPI/Starlette match routes in
# registration order, and ".../1.csv" would otherwise match the generic
# {report_id} route first (then fail int-conversion with a 422).
@router.get("/reports/{report_id}.csv")
def get_report_csv(
    report_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    report = _load_report_or_404(db, tenant_id, report_id)
    content = insight_report_service.build_report_csv_bytes(report)
    return StreamingResponse(
        BytesIO(content), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report['report_ref']}.csv"},
    )


@router.get("/reports/{report_id}.xlsx")
def get_report_xlsx(
    report_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    report = _load_report_or_404(db, tenant_id, report_id)
    content = insight_report_service.build_report_xlsx_bytes(report)
    return StreamingResponse(
        BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={report['report_ref']}.xlsx"},
    )


@router.get("/reports/{report_id}.pdf")
def get_report_pdf(
    report_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    report = _load_report_or_404(db, tenant_id, report_id)
    content = insight_report_service.build_report_pdf_bytes(report)
    return StreamingResponse(
        BytesIO(content), media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={report['report_ref']}.pdf"},
    )


@router.get("/reports/{report_id}")
def get_report(
    report_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return _load_report_or_404(db, tenant_id, report_id)


# ---------------------------------------------------------------------------
# Section 7 — Enterprise Forecast Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard")
def get_dashboard(
    request: Request, horizon: str = Query("30_day"), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        intelligence = insight_engine_service.generate_predictive_intelligence(db, tenant_id, horizon=horizon)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return insight_engine_service.build_forecast_dashboard(intelligence)
