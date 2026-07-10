"""v2.9 — LumenAI Quality: Closed-Loop Quality Intelligence routes (Project Guardian).

Route: /quality-command-center (frontend). API prefix: /api/quality-guardian.

  * POST /events, POST /events/import-csv, GET /events, GET /events/{id}   — Section 1
  * POST /events/{id}/classify                                            — Section 2
  * GET/POST /taxonomy                                                    — Section 3
  * POST /events/{id}/correlate, GET /events/{id}/correlations,
    POST /correlations/{id}/confirm                                      — Section 4
  * POST /events/{id}/rca-draft, GET/PATCH /rca-drafts/{id},
    POST /rca-drafts/{id}/approve|reject                                 — Section 5
  * POST /capa-recommendations/generate, GET /capa-recommendations,
    POST /capa-recommendations/{id}/accept|dismiss,
    GET /capas, POST /capas/{id}/advance                                 — Section 6
  * POST /competency-opportunities/detect, GET /competency-opportunities,
    POST /competency-opportunities/{id}/address,
    GET /competency-opportunities/{id}/effectiveness                     — Section 7
  * GET /first-pass-yield, GET /first-pass-yield/all-scopes              — Section 8
  * GET /command-center                                                  — Section 9
  * POST /events/{id}/confirm, POST /events/{id}/learning-loop           — Section 10
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.quality_guardian import SOURCE_SYSTEMS
from app.services import (
    capa_lifecycle_service,
    capa_recommendation_service,
    competency_intelligence_service,
    event_correlation_service,
    first_pass_yield_service,
    quality_command_center_service,
    quality_event_service,
    quality_taxonomy_service,
    rca_engine_service,
)

router = APIRouter(prefix="/api/quality-guardian", tags=["quality-guardian"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


class EventIn(BaseModel):
    event_date: datetime
    narrative: str = Field(..., min_length=1)
    source_system: str = Field("manual", description=f"One of {SOURCE_SYSTEMS}")
    external_event_id: str = ""
    facility_name: str = ""
    procedure: str = ""
    service_line: str = ""
    case_id: int | None = None
    reporter_role: str = ""
    severity: str = Field("medium", pattern="^(low|medium|high|critical)$")
    attachments: list[str] = Field(default_factory=list)


class CsvImportIn(BaseModel):
    source_system: str
    rows: list[dict]


class TaxonomyTermIn(BaseModel):
    category: str
    term: str
    display_label: str = ""


class ConfirmIn(BaseModel):
    confirmed_by: str = ""


class RcaEditIn(BaseModel):
    supervisor_edits: str = ""


class RcaApproveIn(BaseModel):
    root_cause: str
    approved_by: str = ""


class RcaRejectIn(BaseModel):
    rejected_by: str = ""
    reason: str = ""


class RecommendationGenerateIn(BaseModel):
    event_id: int | None = None
    rca_draft_id: int | None = None


class RecommendationAcceptIn(BaseModel):
    title: str
    owner: str
    due_date: str | None = None


class CapaAdvanceIn(BaseModel):
    new_status: str


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Section 1-2 — Quality Event Intake + Classification
# ---------------------------------------------------------------------------


@router.post("/events", status_code=201)
def post_event(
    body: EventIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = quality_event_service.create_event(db, tenant_id, **body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="quality_guardian.event_created", resource_type="quality_event", resource_id=str(result["id"]),
        details={"event_ref": result["event_ref"], "source_system": result["source_system"]},
    )
    return result


@router.post("/events/import-csv")
def post_import_csv(
    body: CsvImportIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return quality_event_service.import_events_csv(db, tenant_id, body.rows, source_system=body.source_system)


@router.get("/events")
def get_events(
    request: Request, severity: str = Query(""), finding_type: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"events": quality_event_service.list_events(db, tenant_id, severity=severity, finding_type=finding_type)}


@router.post("/events/{event_id}/classify")
def post_classify_event(
    event_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return quality_event_service.classify_event(db, tenant_id, event_id)
    except quality_event_service.QualityEventNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/events/{event_id}/confirm")
def post_confirm_event(
    event_id: int, body: ConfirmIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return quality_event_service.confirm_event(db, tenant_id, event_id, confirmed_by=body.confirmed_by or _actor(current_user))
    except quality_event_service.QualityEventNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/events/{event_id}/learning-loop")
def post_learning_loop(
    event_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return quality_command_center_service.apply_learning_loop(db, tenant_id, event_id)
    except quality_event_service.QualityEventNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/events/{event_id}/correlate")
def post_correlate_event(
    event_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return {"correlations": event_correlation_service.correlate_event(db, tenant_id, event_id)}
    except quality_event_service.QualityEventNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/events/{event_id}/correlations")
def get_correlations(
    event_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"correlations": event_correlation_service.list_correlations(db, tenant_id, event_id)}


@router.post("/events/{event_id}/rca-draft", status_code=201)
def post_generate_rca_draft(
    event_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return rca_engine_service.generate_rca_draft(db, tenant_id, event_id)
    except quality_event_service.QualityEventNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/events/{event_id}")
def get_event(
    event_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return quality_event_service.get_event(db, tenant_id, event_id)
    except quality_event_service.QualityEventNotFoundError as exc:
        raise _not_found(exc) from exc


# ---------------------------------------------------------------------------
# Section 3 — SPD Quality Taxonomy
# ---------------------------------------------------------------------------


@router.get("/taxonomy")
def get_taxonomy(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return quality_taxonomy_service.list_taxonomy(db, tenant_id)


@router.post("/taxonomy", status_code=201)
def post_taxonomy_term(
    body: TaxonomyTermIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return quality_taxonomy_service.add_taxonomy_term(
        db, tenant_id, category=body.category, term=body.term, display_label=body.display_label,
    )


# ---------------------------------------------------------------------------
# Section 4 — correlation confirmation
# ---------------------------------------------------------------------------


@router.post("/correlations/{correlation_id}/confirm")
def post_confirm_correlation(
    correlation_id: int, body: ConfirmIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return event_correlation_service.confirm_correlation(
            db, tenant_id, correlation_id, confirmed_by=body.confirmed_by or _actor(current_user),
        )
    except quality_event_service.QualityEventNotFoundError as exc:
        raise _not_found(exc) from exc


# ---------------------------------------------------------------------------
# Section 5 — AI-Assisted RCA
# ---------------------------------------------------------------------------


@router.get("/rca-drafts/{draft_id}")
def get_rca_draft(
    draft_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return rca_engine_service.get_draft(db, tenant_id, draft_id)
    except rca_engine_service.RCADraftNotFoundError as exc:
        raise _not_found(exc) from exc


@router.patch("/rca-drafts/{draft_id}")
def patch_rca_draft(
    draft_id: int, body: RcaEditIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return rca_engine_service.update_draft(db, tenant_id, draft_id, supervisor_edits=body.supervisor_edits)
    except rca_engine_service.RCADraftNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/rca-drafts/{draft_id}/approve")
def post_approve_rca_draft(
    draft_id: int, body: RcaApproveIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = rca_engine_service.approve_draft(
            db, tenant_id, draft_id, root_cause=body.root_cause, approved_by=body.approved_by or _actor(current_user),
        )
    except rca_engine_service.RCADraftNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="quality_guardian.rca_approved", resource_type="rca_draft", resource_id=str(draft_id),
        details={"root_cause": body.root_cause},
    )
    return result


@router.post("/rca-drafts/{draft_id}/reject")
def post_reject_rca_draft(
    draft_id: int, body: RcaRejectIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return rca_engine_service.reject_draft(
            db, tenant_id, draft_id, rejected_by=body.rejected_by or _actor(current_user), reason=body.reason,
        )
    except rca_engine_service.RCADraftNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 6 — CAPA Recommendation Engine + Lifecycle
# ---------------------------------------------------------------------------


@router.post("/capa-recommendations/generate", status_code=201)
def post_generate_recommendations(
    body: RecommendationGenerateIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {
        "recommendations": capa_recommendation_service.generate_recommendations(
            db, tenant_id, event_id=body.event_id, rca_draft_id=body.rca_draft_id,
        ),
    }


@router.get("/capa-recommendations")
def get_recommendations(
    request: Request, status: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"recommendations": capa_recommendation_service.list_recommendations(db, tenant_id, status=status)}


@router.post("/capa-recommendations/{recommendation_id}/accept")
def post_accept_recommendation(
    recommendation_id: int, body: RecommendationAcceptIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        result = capa_recommendation_service.accept_recommendation(
            db, tenant_id, recommendation_id, title=body.title, owner=body.owner, due_date=body.due_date,
            decided_by=_actor(current_user),
        )
    except capa_recommendation_service.RecommendationNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="quality_guardian.capa_created", resource_type="capa", resource_id=str(result["created_capa_id"]),
        details={"recommendation_type": result["recommendation_type"]},
    )
    return result


@router.post("/capa-recommendations/{recommendation_id}/dismiss")
def post_dismiss_recommendation(
    recommendation_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return capa_recommendation_service.dismiss_recommendation(db, tenant_id, recommendation_id, decided_by=_actor(current_user))
    except capa_recommendation_service.RecommendationNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/capas")
def get_capas(
    request: Request, lifecycle_status: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"capas": capa_lifecycle_service.list_capas(tenant_id, lifecycle_status=lifecycle_status)}


@router.post("/capas/{capa_id}/advance")
def post_advance_capa(
    capa_id: str, body: CapaAdvanceIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return capa_lifecycle_service.advance_lifecycle(tenant_id, capa_id, body.new_status, actor=_actor(current_user))
    except capa_lifecycle_service.InvalidLifecycleTransitionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 7 — Competency Intelligence
# ---------------------------------------------------------------------------


@router.post("/competency-opportunities/detect")
def post_detect_opportunities(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"opportunities": competency_intelligence_service.detect_competency_opportunities(db, tenant_id)}


@router.get("/competency-opportunities")
def get_opportunities(
    request: Request, status: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"opportunities": competency_intelligence_service.list_opportunities(db, tenant_id, status=status)}


@router.post("/competency-opportunities/{opportunity_id}/address")
def post_address_opportunity(
    opportunity_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = competency_intelligence_service.mark_addressed(db, tenant_id, opportunity_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Competency opportunity {opportunity_id} not found.")
    return result


@router.get("/competency-opportunities/{opportunity_id}/effectiveness")
def get_opportunity_effectiveness(
    opportunity_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = competency_intelligence_service.track_effectiveness(db, tenant_id, opportunity_id)
    if result is None:
        return {"effectiveness_score": None, "note": "Not enough recorded activity before/after to compare yet."}
    return result


# ---------------------------------------------------------------------------
# Section 8 — First Pass Yield Intelligence
# ---------------------------------------------------------------------------


@router.get("/first-pass-yield/all-scopes")
def get_fpy_all_scopes(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return first_pass_yield_service.compute_all_scopes(db, tenant_id)


@router.get("/first-pass-yield")
def get_fpy(
    request: Request, scope_type: str = Query(...), scope_value: str = Query(default=None),
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return first_pass_yield_service.compute_first_pass_yield(db, tenant_id, scope_type=scope_type, scope_value=scope_value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 9 — Executive Quality Dashboard
# ---------------------------------------------------------------------------


@router.get("/command-center")
def get_command_center(
    request: Request, days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return quality_command_center_service.quality_command_center_summary(db, tenant_id, days=days)
