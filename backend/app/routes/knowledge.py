"""v1.8 — Institutional Knowledge & Clinical Memory.

- GET/POST /api/knowledge/articles                       — Deliverable 1
- GET/PATCH /api/knowledge/articles/{id}                 — Deliverable 1
- POST /api/knowledge/articles/{id}/{submit-for-review,approve,reject,archive} — Deliverable 9
- GET  /api/knowledge/cases, /api/knowledge/cases/{id}    — Deliverable 2
- POST /api/inspections/{id}/teaching-point               — Deliverable 3
- POST /api/knowledge/search                              — Deliverable 4
- GET  /api/inspections/{id}/similar-cases                — Deliverable 5
- GET/POST /api/knowledge/standards                       — Deliverable 6
- GET  /api/knowledge/competency-topics[/{finding_type}]  — Deliverable 7
- POST /api/knowledge/assistant                           — Deliverable 8
- GET  /api/knowledge/governance-summary                  — Deliverable 9
- GET  /api/knowledge/analytics                           — Deliverable 10
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.knowledge import ARTICLE_CATEGORIES, PENDING_REVIEW, STANDARD_TYPES, TEACHING_POINT
from app.services import knowledge_governance_service as governance
from app.services import knowledge_repository_service as repository
from app.services import organization_standards_service as standards
from app.services.ai_knowledge_assistant_service import answer_question
from app.services.clinical_case_library_service import case_to_dict, list_cases, record_view as record_case_view, save_or_update_case
from app.services.competency_knowledge_service import competency_topic, list_competency_topics
from app.services.knowledge_analytics_service import knowledge_analytics
from app.services.knowledge_search_service import smart_search
from app.services.readiness_engine import get_primary_finding_type
from app.services.similar_case_finder_service import find_similar_cases

router = APIRouter(tags=["institutional-knowledge"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _get_inspection(db: Session, tenant_id: str, inspection_id: int):
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return insp


# ── Institutional Knowledge Repository (Deliverable 1) ──────────────────────

class ArticleIn(BaseModel):
    category: str = Field(..., description=f"One of {ARTICLE_CATEGORIES}")
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    applicable_instruments: list[str] = Field(default_factory=list)
    applicable_findings: list[str] = Field(default_factory=list)
    applicable_manufacturers: list[str] = Field(default_factory=list)
    anatomy_zone: str = Field("", max_length=100)
    procedure: str = Field("", max_length=200)
    specialty: str = Field("", max_length=100)


@router.post("/api/knowledge/articles", status_code=201)
def post_article(
    body: ArticleIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    if body.category not in ARTICLE_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"category must be one of {ARTICLE_CATEGORIES}")
    tenant_id = _tenant(current_user, request)
    row = repository.create_article(
        db, tenant_id=tenant_id, category=body.category, title=body.title, body=body.body,
        author=_actor(current_user), applicable_instruments=body.applicable_instruments,
        applicable_findings=body.applicable_findings, applicable_manufacturers=body.applicable_manufacturers,
        anatomy_zone=body.anatomy_zone, procedure=body.procedure, specialty=body.specialty,
        approval_status=PENDING_REVIEW,
    )
    db.commit()
    db.refresh(row)
    return repository.article_to_dict(row)


@router.get("/api/knowledge/articles")
def get_articles(
    request: Request, category: str = "", instrument: str = "", manufacturer: str = "",
    anatomy_zone: str = "", finding: str = "", procedure: str = "", specialty: str = "",
    approval_status: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {
        "articles": repository.list_articles(
            db, tenant_id, category=category, instrument=instrument, manufacturer=manufacturer,
            anatomy_zone=anatomy_zone, finding=finding, procedure=procedure, specialty=specialty,
            approval_status=approval_status,
        ),
    }


@router.get("/api/knowledge/articles/{article_id}")
def get_article(
    article_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = repository.record_view(db, tenant_id, article_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Knowledge article not found.")
    db.commit()
    return repository.article_to_dict(row)


class ArticleUpdateIn(BaseModel):
    title: str | None = Field(None, max_length=255)
    body: str | None = None


@router.patch("/api/knowledge/articles/{article_id}")
def patch_article(
    article_id: int, body: ArticleUpdateIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = repository.update_article(db, tenant_id, article_id, title=body.title, body=body.body)
    if row is None:
        raise HTTPException(status_code=404, detail="Knowledge article not found.")
    db.commit()
    db.refresh(row)
    return repository.article_to_dict(row)


# ── Knowledge Governance (Deliverable 9) ────────────────────────────────────

@router.post("/api/knowledge/articles/{article_id}/submit-for-review")
def post_submit_for_review(
    article_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        row = governance.submit_for_review(db, tenant_id, article_id)
    except governance.ArticleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return {"id": row.id, "approval_status": row.approval_status}


@router.post("/api/knowledge/articles/{article_id}/approve")
def post_approve_article(
    article_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        row = governance.approve_article(db, tenant_id, article_id, reviewer=_actor(current_user))
    except governance.ArticleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return {"id": row.id, "approval_status": row.approval_status, "reviewer": row.reviewer}


@router.post("/api/knowledge/articles/{article_id}/reject")
def post_reject_article(
    article_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        row = governance.reject_article(db, tenant_id, article_id, reviewer=_actor(current_user))
    except governance.ArticleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return {"id": row.id, "approval_status": row.approval_status, "reviewer": row.reviewer}


@router.post("/api/knowledge/articles/{article_id}/archive")
def post_archive_article(
    article_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        row = governance.archive_article(db, tenant_id, article_id, reviewer=_actor(current_user))
    except governance.ArticleNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return {"id": row.id, "approval_status": row.approval_status}


@router.get("/api/knowledge/governance-summary")
def get_governance_summary(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return governance.governance_summary(db, _tenant(current_user, request))


# ── Clinical Case Library (Deliverable 2) ───────────────────────────────────

@router.get("/api/knowledge/cases")
def get_cases(
    request: Request, instrument: str = "", finding: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"cases": list_cases(db, tenant_id, instrument=instrument, finding=finding)}


@router.get("/api/knowledge/cases/{case_id}")
def get_case_detail(
    case_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = record_case_view(db, tenant_id, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Clinical case not found.")
    db.commit()
    return case_to_dict(row)


@router.get("/api/inspections/{inspection_id}/similar-cases")
def get_similar_cases(
    inspection_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    insp = _get_inspection(db, tenant_id, inspection_id)
    finding_type = get_primary_finding_type(db, insp)
    return {
        "inspection_id": inspection_id,
        "finding_type": finding_type,
        "similar_cases": find_similar_cases(
            db, tenant_id, instrument_type=insp.instrument_type, finding_type=finding_type,
            exclude_inspection_id=inspection_id,
        ),
    }


# ── Supervisor Knowledge Capture (Deliverable 3) ────────────────────────────

class TeachingPointIn(BaseModel):
    explanation: str = Field(..., min_length=1)
    teaching_point: str = Field(..., min_length=1, max_length=255)
    common_mistake: str = Field("", max_length=2000)
    prevention_tip: str = Field("", max_length=2000)
    references: str = Field("", max_length=2000)


@router.post("/api/inspections/{inspection_id}/teaching-point", status_code=201)
def post_teaching_point(
    inspection_id: int, body: TeachingPointIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    """After a disposition override, a supervisor may capture what future
    technicians should know. Authored by a supervisor at the point of a
    real clinical decision, so it is auto-approved rather than routed
    through the general review queue — the same authority already granted
    to disposition overrides (v1.6)."""
    tenant_id = _tenant(current_user, request)
    insp = _get_inspection(db, tenant_id, inspection_id)
    finding_type = get_primary_finding_type(db, insp)

    row = repository.create_article(
        db, tenant_id=tenant_id, category=TEACHING_POINT, title=body.teaching_point, body=body.explanation,
        author=_actor(current_user), applicable_instruments=[insp.instrument_type],
        applicable_findings=[finding_type] if finding_type else [],
        common_mistake=body.common_mistake, prevention_tip=body.prevention_tip, references=body.references,
        source_inspection_id=inspection_id, approval_status="approved",
    )
    row.reviewer = _actor(current_user)
    save_or_update_case(
        db, tenant_id, insp, finding_type=finding_type,
        educational_notes=f"{body.teaching_point}: {body.explanation}",
    )
    db.commit()
    db.refresh(row)
    return repository.article_to_dict(row)


# ── Smart Knowledge Search (Deliverable 4) ──────────────────────────────────

class SearchIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


@router.post("/api/knowledge/search")
def post_search(
    body: SearchIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = smart_search(db, tenant_id, body.query, actor=_actor(current_user))
    db.commit()
    return result


# ── AI Knowledge Assistant (Deliverable 8) ──────────────────────────────────

class AssistantIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    instrument_type: str = Field("", max_length=100)


@router.post("/api/knowledge/assistant")
def post_assistant(
    body: AssistantIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = answer_question(
        db, tenant_id, body.question, instrument_type=body.instrument_type, actor=_actor(current_user),
    )
    db.commit()
    return result


# ── Organization Standards (Deliverable 6) ──────────────────────────────────

class StandardIn(BaseModel):
    standard_type: str = Field(..., description=f"One of {STANDARD_TYPES}")
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)


@router.post("/api/knowledge/standards", status_code=201)
def post_standard(
    body: StandardIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    if body.standard_type not in STANDARD_TYPES:
        raise HTTPException(status_code=422, detail=f"standard_type must be one of {STANDARD_TYPES}")
    tenant_id = _tenant(current_user, request)
    row = standards.create_standard(
        db, tenant_id, standard_type=body.standard_type, title=body.title, description=body.description,
        created_by=_actor(current_user),
    )
    db.commit()
    db.refresh(row)
    return standards.standard_to_dict(row)


@router.get("/api/knowledge/standards")
def get_standards(
    request: Request, standard_type: str = "", db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"standards": standards.list_standards(db, tenant_id, standard_type=standard_type)}


@router.post("/api/knowledge/standards/{standard_id}/deactivate")
def post_deactivate_standard(
    standard_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = standards.deactivate_standard(db, tenant_id, standard_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Organization standard not found.")
    db.commit()
    return standards.standard_to_dict(row)


# ── Competency Knowledge Library (Deliverable 7) ────────────────────────────

@router.get("/api/knowledge/competency-topics")
def get_competency_topics(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"topics": list_competency_topics(db, tenant_id)}


@router.get("/api/knowledge/competency-topics/{finding_type}")
def get_competency_topic(
    finding_type: str, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    topic = competency_topic(db, tenant_id, finding_type)
    if topic is None:
        raise HTTPException(status_code=404, detail="No competency topic found for that finding type.")
    return topic


# ── Knowledge Analytics (Deliverable 10) ────────────────────────────────────

@router.get("/api/knowledge/analytics")
def get_knowledge_analytics(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return knowledge_analytics(db, _tenant(current_user, request))
