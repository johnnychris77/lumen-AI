"""P19: Industry Standardization, Accreditation Integration & Ecosystem Leadership.

Provides accreditation-program tracking (Joint Commission, DNV, CMS, HFAP,
state survey), a readiness/evidence/risk scoring engine, survey-evidence
package generation, the certification program, and anonymized industry
benchmark publications.

Governance: no raw cross-tenant data is exposed. Benchmark publications are
anonymized aggregates with k-anonymity enforced. Every mutation is audit-logged.
All readiness scores are decision-support indicators requiring human review —
nothing here guarantees accreditation or claims FDA clearance / regulatory
approval.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.db import models
from app.models.network_benchmark import NetworkParticipant

router = APIRouter(prefix="/api/accreditation", tags=["accreditation"])

_ACCREDITORS = {"joint_commission", "dnv", "cms", "hfap", "state"}
_PROGRAM_STATUSES = {"preparing", "scheduled", "surveyed", "accredited", "inactive"}
_EVIDENCE_STATUSES = {"missing", "in_progress", "complete"}
_PACKAGE_TYPES = {"binder", "compliance_report", "audit_evidence"}
_CERT_TYPES = {"certified_site", "baseline_excellence", "inspection_intelligence"}
_CERT_STATUSES = {"applicant", "in_review", "certified", "expired"}

# k-anonymity floor for any industry benchmark publication.
_MIN_NETWORK_PARTICIPANTS = 5

_READINESS_DISCLAIMER = (
    "Readiness scoring is a decision-support indicator requiring human review. "
    "It does not guarantee accreditation; final determination rests with the "
    "accrediting body. No FDA clearance or regulatory approval is claimed."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _audit(db, current_user, action, resource_type, resource_id="", details=None,
           tenant_id="platform"):
    try:
        log_audit_event(
            db,
            tenant_id=tenant_id,
            tenant_name="Accreditation",
            actor_email=getattr(current_user, "email", "unknown"),
            actor_role=getattr(current_user, "role", "executive"),
            action_type=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            details=details or {},
            compliance_flag=True,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Phase 1 — Accreditation Programs
# ---------------------------------------------------------------------------

class ProgramCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    facility_id: str = Field(..., min_length=1)
    accreditor: str
    status: str = Field(default="preparing")
    notes: str = Field(default="")

    @field_validator("accreditor")
    @classmethod
    def _v_acc(cls, v):
        if v not in _ACCREDITORS:
            raise ValueError(f"accreditor must be one of {sorted(_ACCREDITORS)}")
        return v

    @field_validator("status")
    @classmethod
    def _v_status(cls, v):
        if v not in _PROGRAM_STATUSES:
            raise ValueError(f"status must be one of {sorted(_PROGRAM_STATUSES)}")
        return v


def _program_dict(p: models.AccreditationProgram) -> dict:
    return {
        "id": p.id,
        "tenant_id": p.tenant_id,
        "facility_id": p.facility_id,
        "accreditor": p.accreditor,
        "status": p.status,
        "notes": p.notes,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.post("/programs", status_code=201)
def create_program(
    payload: ProgramCreate,
    current_user=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    p = models.AccreditationProgram(
        tenant_id=payload.tenant_id,
        facility_id=payload.facility_id,
        accreditor=payload.accreditor,
        status=payload.status,
        notes=payload.notes,
        created_by=getattr(current_user, "email", "unknown"),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    _audit(db, current_user, "accreditation_program_created", "accreditation_program",
           p.id, {"accreditor": p.accreditor}, tenant_id=p.tenant_id)
    return _program_dict(p)


@router.get("/programs")
def list_programs(
    tenant_id: str | None = Query(default=None),
    accreditor: str | None = Query(default=None),
    _=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    q = db.query(models.AccreditationProgram)
    if tenant_id:
        q = q.filter(models.AccreditationProgram.tenant_id == tenant_id)
    if accreditor:
        q = q.filter(models.AccreditationProgram.accreditor == accreditor)
    rows = q.order_by(models.AccreditationProgram.created_at.desc()).all()
    return {"count": len(rows), "programs": [_program_dict(r) for r in rows]}


@router.patch("/programs/{program_id}")
def update_program_status(
    program_id: int,
    status: str = Query(...),
    current_user=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    if status not in _PROGRAM_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status '{status}'")
    p = db.get(models.AccreditationProgram, program_id)
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")
    p.status = status
    db.commit()
    _audit(db, current_user, "accreditation_program_status_changed",
           "accreditation_program", program_id, {"status": status}, tenant_id=p.tenant_id)
    return _program_dict(p)


# ---------------------------------------------------------------------------
# Phase 1/2 — Evidence Items
# ---------------------------------------------------------------------------

class EvidenceCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    facility_id: str = Field(..., min_length=1)
    accreditor: str
    standard_ref: str = Field(default="")
    category: str = Field(default="general")
    title: str = Field(default="")
    status: str = Field(default="missing")
    is_critical: bool = Field(default=False)
    notes: str = Field(default="")

    @field_validator("accreditor")
    @classmethod
    def _v_acc(cls, v):
        if v not in _ACCREDITORS:
            raise ValueError(f"accreditor must be one of {sorted(_ACCREDITORS)}")
        return v

    @field_validator("status")
    @classmethod
    def _v_status(cls, v):
        if v not in _EVIDENCE_STATUSES:
            raise ValueError(f"status must be one of {sorted(_EVIDENCE_STATUSES)}")
        return v


def _evidence_dict(e: models.EvidenceItem) -> dict:
    return {
        "id": e.id,
        "tenant_id": e.tenant_id,
        "facility_id": e.facility_id,
        "accreditor": e.accreditor,
        "standard_ref": e.standard_ref,
        "category": e.category,
        "title": e.title,
        "status": e.status,
        "is_critical": e.is_critical,
        "notes": e.notes,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
    }


@router.post("/evidence-items", status_code=201)
def create_evidence(
    payload: EvidenceCreate,
    current_user=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    e = models.EvidenceItem(
        tenant_id=payload.tenant_id,
        facility_id=payload.facility_id,
        accreditor=payload.accreditor,
        standard_ref=payload.standard_ref,
        category=payload.category,
        title=payload.title,
        status=payload.status,
        is_critical=payload.is_critical,
        notes=payload.notes,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    _audit(db, current_user, "evidence_item_created", "evidence_item", e.id,
           {"accreditor": e.accreditor, "critical": e.is_critical}, tenant_id=e.tenant_id)
    return _evidence_dict(e)


@router.get("/evidence-items")
def list_evidence(
    tenant_id: str = Query(...),
    facility_id: str | None = Query(default=None),
    accreditor: str | None = Query(default=None),
    _=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    q = db.query(models.EvidenceItem).filter(models.EvidenceItem.tenant_id == tenant_id)
    if facility_id:
        q = q.filter(models.EvidenceItem.facility_id == facility_id)
    if accreditor:
        q = q.filter(models.EvidenceItem.accreditor == accreditor)
    rows = q.all()
    return {"count": len(rows), "evidence_items": [_evidence_dict(r) for r in rows]}


@router.patch("/evidence-items/{item_id}")
def update_evidence_status(
    item_id: int,
    status: str = Query(...),
    current_user=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    if status not in _EVIDENCE_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status '{status}'")
    e = db.get(models.EvidenceItem, item_id)
    if not e:
        raise HTTPException(status_code=404, detail="Evidence item not found")
    e.status = status
    e.updated_at = _utcnow()
    db.commit()
    _audit(db, current_user, "evidence_item_status_changed", "evidence_item", item_id,
           {"status": status}, tenant_id=e.tenant_id)
    return _evidence_dict(e)


# ---------------------------------------------------------------------------
# Phase 2 — Readiness Engine (readiness / evidence-completeness / risk scoring)
# ---------------------------------------------------------------------------

def _score_facility(db: Session, tenant_id: str, facility_id: str,
                    accreditor: str | None) -> dict:
    """Compute evidence-completeness, risk, and overall readiness scores for a
    facility from its tracked evidence items. Pure-ish; shared by GET + snapshot."""
    q = db.query(models.EvidenceItem).filter(
        models.EvidenceItem.tenant_id == tenant_id,
        models.EvidenceItem.facility_id == facility_id,
    )
    if accreditor:
        q = q.filter(models.EvidenceItem.accreditor == accreditor)
    items = q.all()
    total = len(items)

    if total == 0:
        return {
            "tenant_id": tenant_id,
            "facility_id": facility_id,
            "accreditor": accreditor,
            "total_items": 0,
            "evidence_completeness_score": 0.0,
            "risk_score": 100.0,
            "readiness_score": 0.0,
            "readiness_status": "not_ready",
            "breakdown": {"missing": 0, "in_progress": 0, "complete": 0},
            "open_critical_items": 0,
            "human_review_required": True,
            "disclaimer": _READINESS_DISCLAIMER,
        }

    complete = sum(1 for i in items if i.status == "complete")
    in_progress = sum(1 for i in items if i.status == "in_progress")
    missing = sum(1 for i in items if i.status == "missing")
    open_critical = sum(1 for i in items if i.is_critical and i.status != "complete")

    # Evidence completeness: complete counts full, in-progress counts half.
    completeness = (complete + 0.5 * in_progress) / total * 100.0

    # Risk: share of incomplete work, with open critical items weighted heavily.
    incomplete = missing + in_progress
    base_risk = incomplete / total * 100.0
    critical_penalty = min(40.0, open_critical * 15.0)
    risk = min(100.0, round(0.6 * base_risk + critical_penalty, 1))

    # Readiness blends completeness against residual risk.
    readiness = max(0.0, round(0.7 * completeness + 0.3 * (100.0 - risk), 1))

    if open_critical > 0:
        # Any open critical item caps readiness status below "ready".
        readiness = min(readiness, 84.0)

    if readiness >= 85.0:
        status_label = "ready"
    elif readiness >= 65.0:
        status_label = "approaching"
    else:
        status_label = "not_ready"

    return {
        "tenant_id": tenant_id,
        "facility_id": facility_id,
        "accreditor": accreditor,
        "total_items": total,
        "evidence_completeness_score": round(completeness, 1),
        "risk_score": risk,
        "readiness_score": readiness,
        "readiness_status": status_label,
        "breakdown": {"missing": missing, "in_progress": in_progress, "complete": complete},
        "open_critical_items": open_critical,
        "human_review_required": True,
        "disclaimer": _READINESS_DISCLAIMER,
    }


@router.get("/readiness")
def readiness_score(
    tenant_id: str = Query(...),
    facility_id: str = Query(...),
    accreditor: str | None = Query(default=None),
    _=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    """Compute live readiness / evidence-completeness / risk scores for a facility."""
    if accreditor and accreditor not in _ACCREDITORS:
        raise HTTPException(status_code=422, detail=f"Invalid accreditor '{accreditor}'")
    return _score_facility(db, tenant_id, facility_id, accreditor)


class ReadinessSnapshotRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    facility_id: str = Field(..., min_length=1)
    accreditor: str

    @field_validator("accreditor")
    @classmethod
    def _v_acc(cls, v):
        if v not in _ACCREDITORS:
            raise ValueError(f"accreditor must be one of {sorted(_ACCREDITORS)}")
        return v


@router.post("/readiness/snapshot", status_code=201)
def snapshot_readiness(
    payload: ReadinessSnapshotRequest,
    current_user=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    """Persist a reproducible readiness assessment. Audit-logged."""
    scored = _score_facility(db, payload.tenant_id, payload.facility_id, payload.accreditor)
    a = models.ReadinessAssessment(
        tenant_id=payload.tenant_id,
        facility_id=payload.facility_id,
        accreditor=payload.accreditor,
        readiness_score=scored["readiness_score"],
        evidence_completeness_score=scored["evidence_completeness_score"],
        risk_score=scored["risk_score"],
        readiness_status=scored["readiness_status"],
        captured_by=getattr(current_user, "email", "unknown"),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    _audit(db, current_user, "readiness_snapshot_created", "readiness_assessment",
           a.id, {"accreditor": a.accreditor, "readiness_status": a.readiness_status},
           tenant_id=a.tenant_id)
    scored["assessment_id"] = a.id
    scored["captured_at"] = a.captured_at.isoformat() if a.captured_at else None
    return scored


@router.get("/readiness/trend")
def readiness_trend(
    tenant_id: str = Query(...),
    facility_id: str = Query(...),
    accreditor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    _=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    """Historical readiness-assessment snapshots for trend visualization."""
    q = db.query(models.ReadinessAssessment).filter(
        models.ReadinessAssessment.tenant_id == tenant_id,
        models.ReadinessAssessment.facility_id == facility_id,
    )
    if accreditor:
        q = q.filter(models.ReadinessAssessment.accreditor == accreditor)
    rows = q.order_by(models.ReadinessAssessment.captured_at.desc()).limit(limit).all()
    rows = list(reversed(rows))
    return {
        "tenant_id": tenant_id,
        "facility_id": facility_id,
        "points": [
            {
                "captured_at": r.captured_at.isoformat() if r.captured_at else None,
                "readiness_score": r.readiness_score,
                "evidence_completeness_score": r.evidence_completeness_score,
                "risk_score": r.risk_score,
                "readiness_status": r.readiness_status,
            }
            for r in rows
        ],
        "human_review_required": True,
    }


# ---------------------------------------------------------------------------
# Phase 3 — Survey Evidence Packages
# ---------------------------------------------------------------------------

class PackageGenerateRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    facility_id: str = Field(..., min_length=1)
    accreditor: str
    package_type: str = Field(default="binder")

    @field_validator("accreditor")
    @classmethod
    def _v_acc(cls, v):
        if v not in _ACCREDITORS:
            raise ValueError(f"accreditor must be one of {sorted(_ACCREDITORS)}")
        return v

    @field_validator("package_type")
    @classmethod
    def _v_type(cls, v):
        if v not in _PACKAGE_TYPES:
            raise ValueError(f"package_type must be one of {sorted(_PACKAGE_TYPES)}")
        return v


@router.post("/survey-evidence/generate", status_code=201)
def generate_evidence_package(
    payload: PackageGenerateRequest,
    current_user=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    """Generate a survey binder / compliance report / audit evidence package from
    the facility's tracked evidence. Captures a readiness summary. Audit-logged."""
    items = db.query(models.EvidenceItem).filter(
        models.EvidenceItem.tenant_id == payload.tenant_id,
        models.EvidenceItem.facility_id == payload.facility_id,
        models.EvidenceItem.accreditor == payload.accreditor,
    ).all()
    complete = sum(1 for i in items if i.status == "complete")
    scored = _score_facility(db, payload.tenant_id, payload.facility_id, payload.accreditor)

    summary = (
        f"{payload.package_type} for {payload.accreditor}: {complete}/{len(items)} "
        f"evidence items complete; readiness {scored['readiness_score']} "
        f"({scored['readiness_status']}); {scored['open_critical_items']} open critical item(s)."
    )
    pkg = models.SurveyEvidencePackage(
        tenant_id=payload.tenant_id,
        facility_id=payload.facility_id,
        accreditor=payload.accreditor,
        package_type=payload.package_type,
        item_count=len(items),
        complete_count=complete,
        summary=summary,
        generated_by=getattr(current_user, "email", "unknown"),
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    _audit(db, current_user, "evidence_package_generated", "evidence_package", pkg.id,
           {"accreditor": pkg.accreditor, "package_type": pkg.package_type},
           tenant_id=pkg.tenant_id)
    return {
        "id": pkg.id,
        "tenant_id": pkg.tenant_id,
        "facility_id": pkg.facility_id,
        "accreditor": pkg.accreditor,
        "package_type": pkg.package_type,
        "item_count": pkg.item_count,
        "complete_count": pkg.complete_count,
        "readiness": scored,
        "contents": [_evidence_dict(i) for i in items],
        "summary": pkg.summary,
        "generated_at": pkg.generated_at.isoformat() if pkg.generated_at else None,
        "disclaimer": _READINESS_DISCLAIMER,
    }


@router.get("/survey-evidence")
def list_packages(
    tenant_id: str = Query(...),
    facility_id: str | None = Query(default=None),
    _=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    q = db.query(models.SurveyEvidencePackage).filter(
        models.SurveyEvidencePackage.tenant_id == tenant_id)
    if facility_id:
        q = q.filter(models.SurveyEvidencePackage.facility_id == facility_id)
    rows = q.order_by(models.SurveyEvidencePackage.generated_at.desc()).all()
    return {
        "count": len(rows),
        "packages": [
            {
                "id": p.id,
                "facility_id": p.facility_id,
                "accreditor": p.accreditor,
                "package_type": p.package_type,
                "item_count": p.item_count,
                "complete_count": p.complete_count,
                "summary": p.summary,
                "generated_at": p.generated_at.isoformat() if p.generated_at else None,
            }
            for p in rows
        ],
    }


# ---------------------------------------------------------------------------
# Phase 4 — Benchmark Publications (anonymized industry reports, k-anonymity)
# ---------------------------------------------------------------------------

@router.get("/benchmark-publications/annual-report")
def annual_benchmark_report(
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Anonymized annual industry benchmark report built from network aggregates.

    Suppressed below the k-anonymity floor so no participant can be re-identified.
    """
    active = int(
        db.query(sqlfunc.count(NetworkParticipant.id))
        .filter(NetworkParticipant.is_active.is_(True))
        .scalar() or 0
    )
    if active < _MIN_NETWORK_PARTICIPANTS:
        _audit(db, current_user, "benchmark_publication_view", "annual_benchmark_report")
        return {
            "published": False,
            "active_participants": active,
            "message": (
                f"Industry report suppressed: fewer than {_MIN_NETWORK_PARTICIPANTS} "
                f"active participants (k-anonymity)."
            ),
            "disclaimer": _READINESS_DISCLAIMER,
        }

    by_type_rows = (
        db.query(NetworkParticipant.facility_type, sqlfunc.count(NetworkParticipant.id))
        .filter(NetworkParticipant.is_active.is_(True))
        .group_by(NetworkParticipant.facility_type).all()
    )
    by_region_rows = (
        db.query(NetworkParticipant.region, sqlfunc.count(NetworkParticipant.id))
        .filter(NetworkParticipant.is_active.is_(True))
        .group_by(NetworkParticipant.region).all()
    )
    _audit(db, current_user, "benchmark_publication_view", "annual_benchmark_report")
    return {
        "published": True,
        "report_type": "annual_industry_benchmark",
        "generated_at": _utcnow().isoformat(),
        "active_participants": active,
        "participant_mix": {
            "by_facility_type": {t or "unknown": c for t, c in by_type_rows},
            "by_region": {r or "unknown": c for r, c in by_region_rows},
        },
        "methodology": {
            "anonymization": "rotating pseudonyms; coarse attributes only",
            "k_anonymity_floor": _MIN_NETWORK_PARTICIPANTS,
            "noise": "Laplace noise applied to published aggregates",
            "human_review_required": True,
        },
        "disclaimer": (
            "Anonymized aggregate industry benchmark. Contamination/quality "
            "indicators are candidate signals requiring human review. No FDA "
            "clearance, regulatory approval, or causation is claimed."
        ),
    }


# ---------------------------------------------------------------------------
# Phase 5 — Certification Program
# ---------------------------------------------------------------------------

class CertificationCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    facility_id: str = Field(..., min_length=1)
    certification_type: str
    level: str = Field(default="standard")
    notes: str = Field(default="")

    @field_validator("certification_type")
    @classmethod
    def _v_type(cls, v):
        if v not in _CERT_TYPES:
            raise ValueError(f"certification_type must be one of {sorted(_CERT_TYPES)}")
        return v


def _cert_dict(c: models.CertifiedSite) -> dict:
    return {
        "id": c.id,
        "tenant_id": c.tenant_id,
        "facility_id": c.facility_id,
        "certification_type": c.certification_type,
        "level": c.level,
        "status": c.status,
        "awarded_at": c.awarded_at.isoformat() if c.awarded_at else None,
        "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.post("/certifications", status_code=201)
def create_certification(
    payload: CertificationCreate,
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    c = models.CertifiedSite(
        tenant_id=payload.tenant_id,
        facility_id=payload.facility_id,
        certification_type=payload.certification_type,
        level=payload.level,
        notes=payload.notes,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    _audit(db, current_user, "certification_created", "certified_site", c.id,
           {"certification_type": c.certification_type}, tenant_id=c.tenant_id)
    return _cert_dict(c)


@router.get("/certifications")
def list_certifications(
    tenant_id: str | None = Query(default=None),
    certification_type: str | None = Query(default=None),
    _=Depends(require_roles("admin", "executive", "spd_manager")),
    db: Session = Depends(get_db),
):
    q = db.query(models.CertifiedSite)
    if tenant_id:
        q = q.filter(models.CertifiedSite.tenant_id == tenant_id)
    if certification_type:
        q = q.filter(models.CertifiedSite.certification_type == certification_type)
    rows = q.order_by(models.CertifiedSite.created_at.desc()).all()
    return {"count": len(rows), "certifications": [_cert_dict(r) for r in rows]}


@router.post("/certifications/{cert_id}/award")
def award_certification(
    cert_id: int,
    valid_days: int = Query(default=365, ge=1, le=1825),
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Award/renew a certification. Sets status=certified with an expiry window."""
    from datetime import timedelta
    c = db.get(models.CertifiedSite, cert_id)
    if not c:
        raise HTTPException(status_code=404, detail="Certification not found")
    now = _utcnow()
    c.status = "certified"
    c.awarded_at = now
    c.expires_at = now + timedelta(days=valid_days)
    db.commit()
    _audit(db, current_user, "certification_awarded", "certified_site", cert_id,
           {"valid_days": valid_days}, tenant_id=c.tenant_id)
    return _cert_dict(c)


# ---------------------------------------------------------------------------
# Phase 7 — Growth / Industry-Leadership KPIs
# ---------------------------------------------------------------------------

@router.get("/kpis")
def accreditation_kpis(
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Accreditation & industry-leadership KPIs."""
    accredited = int(
        db.query(sqlfunc.count(models.AccreditationProgram.id))
        .filter(models.AccreditationProgram.status == "accredited").scalar() or 0
    )
    programs = int(db.query(sqlfunc.count(models.AccreditationProgram.id)).scalar() or 0)
    certified = int(
        db.query(sqlfunc.count(models.CertifiedSite.id))
        .filter(models.CertifiedSite.status == "certified").scalar() or 0
    )
    active_participants = int(
        db.query(sqlfunc.count(NetworkParticipant.id))
        .filter(NetworkParticipant.is_active.is_(True)).scalar() or 0
    )
    return {
        "kpis": [
            {"name": "Accreditation programs tracked", "value": programs, "target": 50},
            {"name": "Accredited facilities", "value": accredited, "target": 30},
            {"name": "Certified sites", "value": certified, "target": 25},
            {"name": "Benchmark network participants", "value": active_participants, "target": 50},
        ],
        "human_review_required": True,
        "disclaimer": _READINESS_DISCLAIMER,
    }
