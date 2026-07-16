"""Project Atlas Sprint 1 — Baseline Image Library REST surface.

Mirrors the CRUD+review pattern already established in
``app.routes.dataset_registry`` (typed service exceptions -> HTTP status
codes, a ``_link_view``-style serializer, an audit event after every
state-changing call) rather than inventing a new convention.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.audit_log import AuditLog
from app.models.baseline_image_library import (
    BaselineImageLink,
    BaselineImageReview,
    BaselineSet,
    BaselineSetMember,
)
from app.services import baseline_compatibility_service as compat_service
from app.services import baseline_image_library_service as bil

router = APIRouter(tags=["baseline-image-library"])

# Section 13 RBAC. Reuses the exact role vocabulary already established by
# app.models.annotation_database (ROLE_* constants) rather than inventing a
# parallel one.
_CREATE_ROLES = ("admin", "spd_manager", "clinical_reviewer", "operator")
_REVIEW_ROLES = ("admin", "spd_manager", "clinical_reviewer")
_READ_ROLES = ("admin", "spd_manager", "clinical_reviewer", "operator", "viewer", "ai_researcher")


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _role(user) -> str:
    return getattr(user, "role", "")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _get_link_or_404(db: Session, link_id: int, tenant_id: str) -> BaselineImageLink:
    row = (
        db.query(BaselineImageLink)
        .filter(BaselineImageLink.id == link_id, BaselineImageLink.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Baseline image link {link_id} not found.")
    return row


def _link_view(row: BaselineImageLink) -> dict:
    return {
        "id": row.id, "tenant_id": row.tenant_id, "facility_id": row.facility_id,
        "baseline_library_entry_id": row.baseline_library_entry_id, "lcid_image_id": row.lcid_image_id,
        "instrument_family": row.instrument_family, "manufacturer": row.manufacturer,
        "model_name": row.model_name, "catalog_number": row.catalog_number,
        "anatomy_zone": row.anatomy_zone, "inspection_view": row.inspection_view, "orientation": row.orientation,
        "image_type": row.image_type, "source_type": row.source_type,
        "source_organization": row.source_organization, "source_reference": row.source_reference,
        "baseline_version": row.baseline_version,
        "effective_date": row.effective_date.isoformat() if row.effective_date else None,
        "lifecycle_status": row.lifecycle_status,
        "approved_by": row.approved_by, "approved_at": row.approved_at.isoformat() if row.approved_at else None,
        "usage_rights_status": row.usage_rights_status, "image_quality_status": row.image_quality_status,
        "annotation_ref": row.annotation_ref, "digital_twin_id": row.digital_twin_id,
        "image_sha256": row.image_sha256, "retained_image_id": row.retained_image_id,
        "superseded_at": row.superseded_at.isoformat() if row.superseded_at else None,
        "supersedes_link_id": row.supersedes_link_id,
        "created_by": row.created_by, "superseded_by": row.superseded_by,
        "limitations": row.limitations,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _review_view(row: BaselineImageReview) -> dict:
    return {
        "id": row.id, "baseline_image_link_id": row.baseline_image_link_id,
        "reviewer": row.reviewer, "reviewer_role": row.reviewer_role, "decision": row.decision,
        "rationale": row.rationale, "limitations": row.limitations,
        "source_verification": row.source_verification,
        "anatomy_compatibility_confirmed": row.anatomy_compatibility_confirmed,
        "image_quality_assessment": row.image_quality_assessment,
        "review_date": row.review_date.isoformat() if row.review_date else None,
        "next_review_date": row.next_review_date.isoformat() if row.next_review_date else None,
    }


def _set_view(db: Session, row: BaselineSet) -> dict:
    member_ids = [
        m.baseline_image_link_id
        for m in db.query(BaselineSetMember).filter(BaselineSetMember.baseline_set_id == row.id).all()
    ]
    return {
        "id": row.id, "tenant_id": row.tenant_id, "manufacturer": row.manufacturer, "model_name": row.model_name,
        "instrument_family": row.instrument_family, "anatomy_zone": row.anatomy_zone,
        "view_protocol": row.view_protocol, "orientation_protocol": row.orientation_protocol,
        "version": row.version, "lifecycle_status": row.lifecycle_status, "active": row.active,
        "limitations": row.limitations,
        "effective_date": row.effective_date.isoformat() if row.effective_date else None,
        "supersedes_set_id": row.supersedes_set_id, "baseline_image_link_ids": member_ids,
    }


# ── Baseline image links (Sections 1, 4, 5, 10) ─────────────────────────────

class LinkImageIn(BaseModel):
    facility_id: str = Field("", max_length=100)
    baseline_library_entry_id: int
    lcid_image_id: int
    anatomy_zone: str = Field(..., min_length=1, max_length=60)
    inspection_view: str = Field(..., min_length=1, max_length=60)
    orientation: str = Field("", max_length=60)
    image_type: str = Field(..., max_length=30)
    source_type: str = Field(..., max_length=40)
    source_organization: str = Field("", max_length=255)
    source_reference: str = Field("", max_length=500)
    baseline_version: str = Field("1.0", max_length=40)


@router.post("/baseline-library/images", status_code=201)
def create_baseline_image_link(
    body: LinkImageIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_CREATE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        link = bil.link_lcid_image_to_baseline(
            db, tenant_id=tenant_id, facility_id=body.facility_id,
            baseline_library_entry_id=body.baseline_library_entry_id, lcid_image_id=body.lcid_image_id,
            anatomy_zone=body.anatomy_zone, inspection_view=body.inspection_view, orientation=body.orientation,
            image_type=body.image_type, source_type=body.source_type,
            source_organization=body.source_organization, source_reference=body.source_reference,
            baseline_version=body.baseline_version, created_by=_actor(current_user),
        )
    except bil.BaselineLibraryEntryNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bil.LcidImageNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bil.ProvenanceRequiredError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _link_view(link)


@router.get("/baseline-library/images/{link_id}")
def get_baseline_image_link(
    link_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return _link_view(_get_link_or_404(db, link_id, tenant_id))


@router.get("/baseline-library/images")
def list_baseline_image_links(
    request: Request, baseline_library_entry_id: int | None = None, lifecycle_status: str | None = None,
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    query = db.query(BaselineImageLink).filter(BaselineImageLink.tenant_id == tenant_id)
    if baseline_library_entry_id is not None:
        query = query.filter(BaselineImageLink.baseline_library_entry_id == baseline_library_entry_id)
    if lifecycle_status is not None:
        query = query.filter(BaselineImageLink.lifecycle_status == lifecycle_status)
    rows = query.order_by(BaselineImageLink.id.desc()).all()
    return {"count": len(rows), "images": [_link_view(r) for r in rows]}


@router.post("/baseline-library/images/{link_id}/submit-for-review")
def submit_baseline_image_for_review(
    link_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_CREATE_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    link = _get_link_or_404(db, link_id, tenant_id)
    try:
        link = bil.submit_for_review(db, link=link, actor=_actor(current_user))
    except bil.InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _link_view(link)


class ReviewIn(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    rationale: str = Field(..., min_length=1, max_length=2000)
    limitations: str = Field("", max_length=2000)
    source_verification: str = Field("", max_length=2000)
    anatomy_compatibility_confirmed: bool = False
    image_quality_assessment: str = Field("", max_length=20)
    next_review_date: datetime | None = None


@router.post("/baseline-library/images/{link_id}/review", status_code=201)
def review_baseline_image(
    link_id: int, body: ReviewIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_REVIEW_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    link = _get_link_or_404(db, link_id, tenant_id)
    try:
        review = bil.review_baseline_image(
            db, link=link, reviewer=_actor(current_user), reviewer_role=_role(current_user),
            decision=body.decision, rationale=body.rationale, limitations=body.limitations,
            source_verification=body.source_verification,
            anatomy_compatibility_confirmed=body.anatomy_compatibility_confirmed,
            image_quality_assessment=body.image_quality_assessment, next_review_date=body.next_review_date,
        )
    except bil.PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except bil.InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _review_view(review)


@router.post("/baseline-library/images/{link_id}/activate")
def activate_baseline_image(
    link_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_REVIEW_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    link = _get_link_or_404(db, link_id, tenant_id)
    try:
        link = bil.activate_baseline_image(db, link=link, actor=_actor(current_user), actor_role=_role(current_user))
    except bil.PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except bil.InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except bil.ActivationGateError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "missing": exc.missing}) from exc
    return _link_view(link)


class SuspendIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


@router.post("/baseline-library/images/{link_id}/suspend")
def suspend_baseline_image(
    link_id: int, body: SuspendIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_REVIEW_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    link = _get_link_or_404(db, link_id, tenant_id)
    try:
        link = bil.suspend_baseline_image(
            db, link=link, actor=_actor(current_user), actor_role=_role(current_user), reason=body.reason,
        )
    except bil.PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except bil.InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _link_view(link)


@router.post("/baseline-library/images/{link_id}/archive")
def archive_baseline_image(
    link_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_REVIEW_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    link = _get_link_or_404(db, link_id, tenant_id)
    try:
        link = bil.archive_baseline_image(db, link=link, actor=_actor(current_user), actor_role=_role(current_user))
    except bil.PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except bil.InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _link_view(link)


class SupersedeIn(BaseModel):
    new_link_id: int


@router.post("/baseline-library/images/{link_id}/supersede")
def supersede_baseline_image(
    link_id: int, body: SupersedeIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_REVIEW_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    old_link = _get_link_or_404(db, link_id, tenant_id)
    new_link = _get_link_or_404(db, body.new_link_id, tenant_id)
    try:
        old_link, new_link = bil.supersede_baseline_image(
            db, old_link=old_link, new_link=new_link, actor=_actor(current_user), actor_role=_role(current_user),
        )
    except bil.PermissionDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (bil.InvalidTransitionError, bil.TenantMismatchError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"superseded": _link_view(old_link), "active": _link_view(new_link)}


@router.get("/baseline-library/images/{link_id}/audit-history")
def baseline_image_audit_history(
    link_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    _get_link_or_404(db, link_id, tenant_id)  # 404s + tenant-scopes before exposing any audit rows
    rows = (
        db.query(AuditLog)
        .filter(
            AuditLog.tenant_id == tenant_id, AuditLog.resource_type == "baseline_image_link",
            AuditLog.resource_id == str(link_id),
        )
        .order_by(AuditLog.created_at.asc())
        .all()
    )
    return {
        "count": len(rows),
        "events": [
            {
                "action_type": r.action_type, "actor_email": r.actor_email, "actor_role": r.actor_role,
                "status": r.status, "details": r.details, "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


# ── Compatibility + resolution (Sections 7, 8) ──────────────────────────────

class CandidateIn(BaseModel):
    instrument_family: str = ""
    manufacturer: str = ""
    model_name: str = ""
    anatomy_zone: str = ""
    inspection_view: str = ""
    orientation: str = ""
    image_quality_status: str = ""
    digital_twin_id: str = ""


@router.post("/baseline-library/compatibility-check")
def compatibility_check(
    body: CandidateIn, request: Request, baseline_image_link_id: int | None = None,
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    link = None
    if baseline_image_link_id is not None:
        link = (
            db.query(BaselineImageLink)
            .filter(BaselineImageLink.id == baseline_image_link_id, BaselineImageLink.tenant_id == tenant_id)
            .first()
        )
    candidate = compat_service.CandidateContext(tenant_id=tenant_id, **body.model_dump())
    status_result = compat_service.check_compatibility(candidate=candidate, baseline_link=link)
    return {"status": status_result}


@router.post("/baseline-library/resolve")
def resolve_baseline(
    body: CandidateIn, request: Request, require_exact: bool = False,
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    candidate = compat_service.CandidateContext(tenant_id=tenant_id, **body.model_dump())
    result = compat_service.resolve_baseline_image(db, candidate=candidate, require_exact=require_exact)
    return {
        "baseline_image_link_id": result.baseline_image_link_id, "baseline_set_id": result.baseline_set_id,
        "resolution_scope": result.resolution_scope, "resolution_reason": result.resolution_reason,
        "version": result.version, "limitations": result.limitations,
    }


# ── Baseline sets (Section 6) ────────────────────────────────────────────────

class CreateSetIn(BaseModel):
    manufacturer: str = Field("", max_length=100)
    model_name: str = Field("", max_length=100)
    instrument_family: str = Field("", max_length=100)
    anatomy_zone: str = Field("", max_length=60)
    view_protocol: str = Field("", max_length=60)
    orientation_protocol: str = Field("", max_length=60)
    version: str = Field("1.0", max_length=40)
    limitations: str = Field("", max_length=2000)
    baseline_image_link_ids: list[int] = Field(default_factory=list)


@router.post("/baseline-library/sets", status_code=201)
def create_baseline_set(
    body: CreateSetIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_REVIEW_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = BaselineSet(
        tenant_id=tenant_id, manufacturer=body.manufacturer, model_name=body.model_name,
        instrument_family=body.instrument_family, anatomy_zone=body.anatomy_zone,
        view_protocol=body.view_protocol, orientation_protocol=body.orientation_protocol,
        version=body.version, limitations=body.limitations,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    for link_id in body.baseline_image_link_ids:
        link = _get_link_or_404(db, link_id, tenant_id)
        db.add(BaselineSetMember(baseline_set_id=row.id, baseline_image_link_id=link.id))
    db.commit()
    return _set_view(db, row)


@router.get("/baseline-library/sets/{set_id}")
def get_baseline_set(
    set_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = db.query(BaselineSet).filter(BaselineSet.id == set_id, BaselineSet.tenant_id == tenant_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Baseline set {set_id} not found.")
    return _set_view(db, row)


# ── Legacy migration report (Section 15) ────────────────────────────────────

@router.get("/baseline-library/legacy-report")
def legacy_baseline_report(
    request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = _tenant(current_user, request)
    return bil.legacy_baseline_report(db, tenant_id=tenant_id)
