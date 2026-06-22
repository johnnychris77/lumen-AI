"""P18: National Health System Expansion & Strategic Partnerships.

Adds strategic-partnership tracking, the reference-customer program, a
national growth / market-intelligence summary, and growth KPIs. This router
builds ON existing intelligence infrastructure (/api/network benchmarks,
/api/enterprise/benchmarks, /api/manufacturer-intelligence) rather than
duplicating it.

Governance: no raw cross-tenant data is exposed here. The market-intelligence
summary reports only anonymized aggregate counts (k-anonymity enforced — the
benchmark network is suppressed below the minimum participant threshold).
Reference customers are only externally citable with explicit consent. All
mutations are audit-logged. No clinical or regulatory claims are made.
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

router = APIRouter(prefix="/api/growth", tags=["growth"])

# k-anonymity floor for any national aggregate surfaced through this router.
_MIN_NETWORK_PARTICIPANTS = 5

_PARTNER_TYPES = {"manufacturer", "vendor", "industry_org", "gpo"}
_PARTNER_STATUSES = {"prospect", "engaged", "active", "inactive"}
_CONVERSION_STAGES = ["pilot", "converting", "enterprise", "reference"]


def _audit(db, current_user, action, resource_type, resource_id="", details=None):
    try:
        log_audit_event(
            db,
            tenant_id="platform",
            tenant_name="Growth",
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
# Phase 2 — Strategic Partnerships
# ---------------------------------------------------------------------------

class PartnershipCreate(BaseModel):
    partner_name: str = Field(..., min_length=1)
    partner_type: str
    status: str = Field(default="prospect")
    tier: str = Field(default="standard")
    contact_name: str = Field(default="")
    contact_email: str = Field(default="")
    region: str = Field(default="")
    notes: str = Field(default="")

    @field_validator("partner_type")
    @classmethod
    def _v_type(cls, v):
        if v not in _PARTNER_TYPES:
            raise ValueError(f"partner_type must be one of {sorted(_PARTNER_TYPES)}")
        return v

    @field_validator("status")
    @classmethod
    def _v_status(cls, v):
        if v not in _PARTNER_STATUSES:
            raise ValueError(f"status must be one of {sorted(_PARTNER_STATUSES)}")
        return v


def _partnership_dict(p: models.StrategicPartnership) -> dict:
    return {
        "id": p.id,
        "partner_name": p.partner_name,
        "partner_type": p.partner_type,
        "status": p.status,
        "tier": p.tier,
        "contact_name": p.contact_name,
        "contact_email": p.contact_email,
        "region": p.region,
        "notes": p.notes,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.post("/partnerships", status_code=201)
def create_partnership(
    payload: PartnershipCreate,
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    p = models.StrategicPartnership(
        partner_name=payload.partner_name,
        partner_type=payload.partner_type,
        status=payload.status,
        tier=payload.tier,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        region=payload.region,
        notes=payload.notes,
        created_by=getattr(current_user, "email", "unknown"),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    _audit(db, current_user, "partnership_created", "strategic_partnership", p.id,
           {"partner_type": p.partner_type, "status": p.status})
    return _partnership_dict(p)


@router.get("/partnerships")
def list_partnerships(
    partner_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    q = db.query(models.StrategicPartnership)
    if partner_type:
        q = q.filter(models.StrategicPartnership.partner_type == partner_type)
    if status:
        q = q.filter(models.StrategicPartnership.status == status)
    rows = q.order_by(models.StrategicPartnership.created_at.desc()).all()
    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r.partner_type] = by_type.get(r.partner_type, 0) + 1
    return {"count": len(rows), "by_type": by_type,
            "partnerships": [_partnership_dict(r) for r in rows]}


@router.patch("/partnerships/{partnership_id}")
def update_partnership_status(
    partnership_id: int,
    status: str = Query(...),
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    if status not in _PARTNER_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status '{status}'")
    p = db.get(models.StrategicPartnership, partnership_id)
    if not p:
        raise HTTPException(status_code=404, detail="Partnership not found")
    p.status = status
    db.commit()
    _audit(db, current_user, "partnership_status_changed", "strategic_partnership",
           partnership_id, {"status": status})
    return _partnership_dict(p)


# ---------------------------------------------------------------------------
# Phase 3 — Reference Customer Program
# ---------------------------------------------------------------------------

class ReferenceCreate(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    display_name: str = Field(default="")
    facility_type: str = Field(default="hospital")
    region: str = Field(default="")
    conversion_stage: str = Field(default="pilot")
    modeled_annual_savings_usd: float = Field(default=0.0, ge=0)
    notes: str = Field(default="")

    @field_validator("conversion_stage")
    @classmethod
    def _v_stage(cls, v):
        if v not in _CONVERSION_STAGES:
            raise ValueError(f"conversion_stage must be one of {_CONVERSION_STAGES}")
        return v


def _reference_dict(r: models.ReferenceCustomer, *, redact: bool = True) -> dict:
    """Serialize a reference customer. When redact=True (default), identifying
    fields are masked unless the customer has consented to public reference."""
    citable = bool(r.public_reference_consent)
    name = r.display_name if (citable or not redact) else f"Reference #{r.id}"
    return {
        "id": r.id,
        "tenant_id": r.tenant_id if not redact else None,
        "display_name": name,
        "facility_type": r.facility_type,
        "region": r.region,
        "conversion_stage": r.conversion_stage,
        "case_study_status": r.case_study_status,
        "testimonial_status": r.testimonial_status,
        "public_reference_consent": citable,
        "modeled_annual_savings_usd": r.modeled_annual_savings_usd,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.post("/reference-customers", status_code=201)
def create_reference(
    payload: ReferenceCreate,
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    r = models.ReferenceCustomer(
        tenant_id=payload.tenant_id,
        display_name=payload.display_name,
        facility_type=payload.facility_type,
        region=payload.region,
        conversion_stage=payload.conversion_stage,
        modeled_annual_savings_usd=payload.modeled_annual_savings_usd,
        notes=payload.notes,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    _audit(db, current_user, "reference_customer_created", "reference_customer", r.id,
           {"conversion_stage": r.conversion_stage})
    return _reference_dict(r, redact=False)


@router.post("/reference-customers/{ref_id}/consent")
def set_reference_consent(
    ref_id: int,
    consent: bool = Query(...),
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Record explicit public-reference consent. Without consent a customer is
    never externally citable (name stays redacted in public listings)."""
    r = db.get(models.ReferenceCustomer, ref_id)
    if not r:
        raise HTTPException(status_code=404, detail="Reference customer not found")
    r.public_reference_consent = consent
    r.updated_at = datetime.now(timezone.utc)
    db.commit()
    _audit(db, current_user, "reference_consent_changed", "reference_customer", ref_id,
           {"consent": consent})
    return _reference_dict(r, redact=False)


@router.get("/reference-customers")
def list_references(
    public_only: bool = Query(default=False),
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """List reference customers. public_only returns only consented references
    (suitable for external case-study use); otherwise internal view with
    identities redacted unless consented."""
    q = db.query(models.ReferenceCustomer)
    if public_only:
        q = q.filter(models.ReferenceCustomer.public_reference_consent.is_(True))
    rows = q.all()
    return {
        "count": len(rows),
        "public_only": public_only,
        "reference_customers": [_reference_dict(r, redact=True) for r in rows],
    }


@router.get("/conversion-funnel")
def conversion_funnel(
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Pilot → converting → enterprise → reference funnel counts and rates."""
    rows = db.query(models.ReferenceCustomer).all()
    stage_counts = {s: 0 for s in _CONVERSION_STAGES}
    for r in rows:
        if r.conversion_stage in stage_counts:
            stage_counts[r.conversion_stage] += 1

    total = len(rows)
    enterprise_plus = stage_counts["enterprise"] + stage_counts["reference"]
    pilot_to_enterprise_rate = round((enterprise_plus / total * 100), 1) if total else 0.0
    return {
        "total_accounts": total,
        "stages": stage_counts,
        "pilot_to_enterprise_conversion_pct": pilot_to_enterprise_rate,
        "disclaimer": "Commercial funnel metrics for internal planning.",
    }


# ---------------------------------------------------------------------------
# Phase 5 — Executive Market Intelligence (national, anonymized aggregates)
# ---------------------------------------------------------------------------

@router.get("/market-intelligence/summary")
def market_intelligence_summary(
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """National market-intelligence summary built from anonymized aggregates.

    The benchmark-network section is suppressed unless the active participant
    count meets the k-anonymity floor, so no individual participant can be
    re-identified.
    """
    active_participants = int(
        db.query(sqlfunc.count(NetworkParticipant.id))
        .filter(NetworkParticipant.is_active.is_(True))
        .scalar() or 0
    )

    # Participant mix by facility type and region (only when above the floor).
    network_section: dict
    if active_participants >= _MIN_NETWORK_PARTICIPANTS:
        by_type_rows = (
            db.query(NetworkParticipant.facility_type,
                     sqlfunc.count(NetworkParticipant.id))
            .filter(NetworkParticipant.is_active.is_(True))
            .group_by(NetworkParticipant.facility_type)
            .all()
        )
        by_region_rows = (
            db.query(NetworkParticipant.region,
                     sqlfunc.count(NetworkParticipant.id))
            .filter(NetworkParticipant.is_active.is_(True))
            .group_by(NetworkParticipant.region)
            .all()
        )
        network_section = {
            "k_anonymity_met": True,
            "active_participants": active_participants,
            "by_facility_type": {t or "unknown": c for t, c in by_type_rows},
            "by_region": {r or "unknown": c for r, c in by_region_rows},
        }
    else:
        network_section = {
            "k_anonymity_met": False,
            "active_participants": active_participants,
            "message": (
                f"Benchmark network detail suppressed: fewer than "
                f"{_MIN_NETWORK_PARTICIPANTS} active participants (k-anonymity)."
            ),
        }

    partnerships_total = int(db.query(sqlfunc.count(models.StrategicPartnership.id)).scalar() or 0)
    active_partnerships = int(
        db.query(sqlfunc.count(models.StrategicPartnership.id))
        .filter(models.StrategicPartnership.status == "active")
        .scalar() or 0
    )
    reference_total = int(db.query(sqlfunc.count(models.ReferenceCustomer.id)).scalar() or 0)
    public_references = int(
        db.query(sqlfunc.count(models.ReferenceCustomer.id))
        .filter(models.ReferenceCustomer.public_reference_consent.is_(True))
        .scalar() or 0
    )

    _audit(db, current_user, "market_intelligence_view", "market_intelligence_summary")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_network": network_section,
        "partnerships": {"total": partnerships_total, "active": active_partnerships},
        "reference_program": {"total": reference_total, "public": public_references},
        "governance": {
            "tenant_isolation": "enforced — no raw cross-tenant data exposed",
            "anonymization": "k-anonymity floor applied to network aggregates",
            "human_review_required": True,
        },
        "disclaimer": "Anonymized aggregate market intelligence for executive planning. "
                      "No FDA clearance or regulatory approval is claimed.",
    }


# ---------------------------------------------------------------------------
# Growth KPIs
# ---------------------------------------------------------------------------

@router.get("/kpis")
def growth_kpis(
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """National growth KPIs aggregating partnerships, references, and network."""
    active_participants = int(
        db.query(sqlfunc.count(NetworkParticipant.id))
        .filter(NetworkParticipant.is_active.is_(True))
        .scalar() or 0
    )
    active_partnerships = int(
        db.query(sqlfunc.count(models.StrategicPartnership.id))
        .filter(models.StrategicPartnership.status == "active")
        .scalar() or 0
    )
    refs = db.query(models.ReferenceCustomer).all()
    enterprise_plus = sum(1 for r in refs if r.conversion_stage in ("enterprise", "reference"))
    conv_rate = round((enterprise_plus / len(refs) * 100), 1) if refs else 0.0

    return {
        "kpis": [
            {"name": "Active benchmark participants", "value": active_participants, "target": 25},
            {"name": "Active strategic partnerships", "value": active_partnerships, "target": 10},
            {"name": "Reference customers", "value": len(refs), "target": 15},
            {"name": "Pilot→Enterprise conversion %", "value": conv_rate, "target": 50, "unit": "%"},
        ],
        "human_review_required": True,
        "disclaimer": "Growth KPIs for internal planning; targets are illustrative.",
    }
