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

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.db import models
from app.models.network_benchmark import NetworkParticipant
from app.routes.commercial import _compute_health

router = APIRouter(prefix="/api/growth", tags=["growth"])

# k-anonymity floor for any national aggregate surfaced through this router.
_MIN_NETWORK_PARTICIPANTS = 5

# A partnership stalled in "engaged" longer than this raises an escalation flag.
_STALLED_ENGAGED_DAYS = 90

_PARTNER_TYPES = {"manufacturer", "vendor", "industry_org", "gpo"}
_PARTNER_STATUSES = {"prospect", "engaged", "active", "inactive"}
_CONVERSION_STAGES = ["pilot", "converting", "enterprise", "reference"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    """Normalize possibly-naive DB timestamps to UTC-aware for safe comparison."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


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
    next_review_date: datetime | None = Field(default=None)

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
    now = _utcnow()
    next_review = _aware(p.next_review_date)
    status_changed = _aware(p.status_changed_at)
    review_overdue = bool(next_review and next_review < now)
    stalled = bool(
        p.status == "engaged" and status_changed
        and (now - status_changed) > timedelta(days=_STALLED_ENGAGED_DAYS)
    )
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
        "next_review_date": next_review.isoformat() if next_review else None,
        "review_overdue": review_overdue,
        "status_changed_at": status_changed.isoformat() if status_changed else None,
        "escalation": stalled,
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
        next_review_date=payload.next_review_date,
        status_changed_at=_utcnow(),
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
    overdue_review: bool = Query(default=False),
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    q = db.query(models.StrategicPartnership)
    if partner_type:
        q = q.filter(models.StrategicPartnership.partner_type == partner_type)
    if status:
        q = q.filter(models.StrategicPartnership.status == status)
    rows = q.order_by(models.StrategicPartnership.created_at.desc()).all()
    dicts = [_partnership_dict(r) for r in rows]
    if overdue_review:
        dicts = [d for d in dicts if d["review_overdue"]]
    by_type: dict[str, int] = {}
    for d in dicts:
        by_type[d["partner_type"]] = by_type.get(d["partner_type"], 0) + 1
    escalations = sum(1 for d in dicts if d["escalation"])
    return {"count": len(dicts), "by_type": by_type, "escalations": escalations,
            "partnerships": dicts}


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
    p.status_changed_at = _utcnow()
    db.commit()
    _audit(db, current_user, "partnership_status_changed", "strategic_partnership",
           partnership_id, {"status": status})
    return _partnership_dict(p)


class PartnershipNoteCreate(BaseModel):
    note: str = Field(..., min_length=1)


@router.post("/partnerships/{partnership_id}/notes", status_code=201)
def add_partnership_note(
    partnership_id: int,
    payload: PartnershipNoteCreate,
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Append a timestamped engagement note / touchpoint. Audit-logged."""
    p = db.get(models.StrategicPartnership, partnership_id)
    if not p:
        raise HTTPException(status_code=404, detail="Partnership not found")
    n = models.PartnershipNote(
        partnership_id=partnership_id,
        note=payload.note,
        author=getattr(current_user, "email", "unknown"),
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    _audit(db, current_user, "partnership_note_added", "strategic_partnership",
           partnership_id, {"note_id": n.id})
    return {
        "id": n.id,
        "partnership_id": n.partnership_id,
        "note": n.note,
        "author": n.author,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/partnerships/{partnership_id}/notes")
def list_partnership_notes(
    partnership_id: int,
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    p = db.get(models.StrategicPartnership, partnership_id)
    if not p:
        raise HTTPException(status_code=404, detail="Partnership not found")
    rows = (
        db.query(models.PartnershipNote)
        .filter(models.PartnershipNote.partnership_id == partnership_id)
        .order_by(models.PartnershipNote.created_at.desc())
        .all()
    )
    return {
        "partnership_id": partnership_id,
        "count": len(rows),
        "notes": [
            {
                "id": n.id,
                "note": n.note,
                "author": n.author,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in rows
        ],
    }


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
        "case_study_url": r.case_study_url if (citable or not redact) else "",
        "case_study_completed_at": (
            r.case_study_completed_at.isoformat() if r.case_study_completed_at else None
        ),
        "testimonial_status": r.testimonial_status,
        "customer_quote": r.customer_quote if (citable or not redact) else "",
        "public_reference_consent": citable,
        "modeled_annual_savings_usd": r.modeled_annual_savings_usd,
        "roi_payback_months": r.roi_payback_months,
        "roi_captured_at": r.roi_captured_at.isoformat() if r.roi_captured_at else None,
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


class ReferenceRoiRequest(BaseModel):
    modeled_annual_savings_usd: float = Field(..., ge=0)
    roi_payback_months: float | None = Field(default=None, ge=0)


@router.post("/reference-customers/{ref_id}/roi")
def set_reference_roi(
    ref_id: int,
    payload: ReferenceRoiRequest,
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Snapshot P17 ROI-calculator output onto the reference record so the
    case study cites a single, auditable savings figure. Audit-logged.

    ROI is modeled and customer-validated — never presented as a guarantee."""
    r = db.get(models.ReferenceCustomer, ref_id)
    if not r:
        raise HTTPException(status_code=404, detail="Reference customer not found")
    r.modeled_annual_savings_usd = payload.modeled_annual_savings_usd
    r.roi_payback_months = payload.roi_payback_months
    r.roi_captured_at = _utcnow()
    r.updated_at = _utcnow()
    db.commit()
    _audit(db, current_user, "reference_roi_captured", "reference_customer", ref_id,
           {"modeled_annual_savings_usd": payload.modeled_annual_savings_usd})
    result = _reference_dict(r, redact=False)
    result["disclaimer"] = "Modeled, customer-validated ROI — not a guarantee."
    return result


@router.get("/reference-customers/{ref_id}/case-study-checklist")
def case_study_checklist(
    ref_id: int,
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Completeness checklist for turning a reference into a citable case study."""
    r = db.get(models.ReferenceCustomer, ref_id)
    if not r:
        raise HTTPException(status_code=404, detail="Reference customer not found")
    items = {
        "public_consent": bool(r.public_reference_consent),
        "roi_captured": r.roi_captured_at is not None,
        "testimonial_approved": r.testimonial_status == "approved",
        "customer_quote": bool(r.customer_quote.strip()),
        "case_study_published": bool(r.case_study_url.strip()),
    }
    complete = all(items.values())
    citable = items["public_consent"] and items["testimonial_approved"]
    return {
        "reference_id": ref_id,
        "checklist": items,
        "complete": complete,
        "externally_citable": citable,
        "completed_count": sum(1 for v in items.values() if v),
        "total_items": len(items),
    }


@router.get("/reference-customers")
def list_references(
    public_only: bool = Query(default=False),
    ready_to_convert: bool = Query(default=False),
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """List reference customers. public_only returns only consented references
    (suitable for external case-study use); otherwise internal view with
    identities redacted unless consented.

    ready_to_convert filters pilot-stage accounts whose tenant health score is
    'healthy' (P17), surfacing pilots that are conversion-ready for CSMs."""
    q = db.query(models.ReferenceCustomer)
    if public_only:
        q = q.filter(models.ReferenceCustomer.public_reference_consent.is_(True))
    rows = q.all()

    if ready_to_convert:
        ready = []
        for r in rows:
            if r.conversion_stage != "pilot":
                continue
            try:
                health = _compute_health(db, r.tenant_id, 100.0, 100.0)
            except Exception:
                continue
            if health.get("status") == "healthy":
                d = _reference_dict(r, redact=True)
                d["health_status"] = health["status"]
                d["composite_score"] = health["composite_score"]
                ready.append(d)
        return {
            "count": len(ready),
            "ready_to_convert": True,
            "reference_customers": ready,
            "human_review_required": True,
        }

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
# Benchmark trend history (anonymized aggregate snapshots, k-anonymity enforced)
# ---------------------------------------------------------------------------

class BenchmarkSnapshotCreate(BaseModel):
    metric_name: str = Field(..., min_length=1)
    cohort: str = Field(default="all")
    cohort_value: str = Field(default="")
    n_participants: int = Field(..., ge=0)
    p50: float = Field(default=0.0)
    mean: float = Field(default=0.0)


@router.post("/benchmark-snapshots", status_code=201)
def create_benchmark_snapshot(
    payload: BenchmarkSnapshotCreate,
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Record an anonymized aggregate benchmark snapshot for trend history.

    Only aggregate values are stored — never per-tenant data. The participant
    count is persisted so reads can enforce k-anonymity."""
    s = models.NetworkBenchmarkSnapshot(
        metric_name=payload.metric_name,
        cohort=payload.cohort,
        cohort_value=payload.cohort_value,
        n_participants=payload.n_participants,
        p50=payload.p50,
        mean=payload.mean,
        captured_by=getattr(current_user, "email", "unknown"),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    _audit(db, current_user, "benchmark_snapshot_created", "network_benchmark_snapshot",
           s.id, {"metric_name": s.metric_name})
    return {"id": s.id, "metric_name": s.metric_name,
            "captured_at": s.captured_at.isoformat() if s.captured_at else None}


@router.get("/benchmark-trends")
def benchmark_trends(
    metric: str = Query(...),
    cohort: str = Query(default="all"),
    days: int = Query(default=90, ge=1, le=730),
    _=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Time-series of an anonymized network benchmark metric. Snapshots below
    the k-anonymity participant floor are suppressed from the series."""
    cutoff = _utcnow() - timedelta(days=days)
    rows = (
        db.query(models.NetworkBenchmarkSnapshot)
        .filter(models.NetworkBenchmarkSnapshot.metric_name == metric)
        .filter(models.NetworkBenchmarkSnapshot.cohort == cohort)
        .order_by(models.NetworkBenchmarkSnapshot.captured_at.asc())
        .all()
    )
    series = []
    suppressed = 0
    for r in rows:
        captured = _aware(r.captured_at)
        if captured and captured < cutoff:
            continue
        if r.n_participants < _MIN_NETWORK_PARTICIPANTS:
            suppressed += 1
            continue
        series.append({
            "captured_at": captured.isoformat() if captured else None,
            "p50": r.p50,
            "mean": r.mean,
            "n_participants": r.n_participants,
        })
    return {
        "metric": metric,
        "cohort": cohort,
        "days": days,
        "points": series,
        "suppressed_below_k": suppressed,
        "human_review_required": True,
        "disclaimer": "Anonymized aggregate trend. No FDA clearance or causation claimed.",
    }


# ---------------------------------------------------------------------------
# Phase 5 — Executive Market Intelligence (national, anonymized aggregates)
# ---------------------------------------------------------------------------

@router.get("/market-intelligence/by-region")
def market_intelligence_by_region(
    current_user=Depends(require_roles("admin", "executive")),
    db: Session = Depends(get_db),
):
    """Per-region participant mix, with k-anonymity enforced *per region* — any
    region below the floor is suppressed so small regions can't be re-identified."""
    rows = (
        db.query(NetworkParticipant.region, NetworkParticipant.facility_type,
                 sqlfunc.count(NetworkParticipant.id))
        .filter(NetworkParticipant.is_active.is_(True))
        .group_by(NetworkParticipant.region, NetworkParticipant.facility_type)
        .all()
    )
    by_region: dict[str, dict] = {}
    for region, ftype, count in rows:
        key = region or "unknown"
        bucket = by_region.setdefault(key, {"total": 0, "by_facility_type": {}})
        bucket["total"] += count
        bucket["by_facility_type"][ftype or "unknown"] = count

    regions_out = {}
    suppressed_regions = []
    for region, data in by_region.items():
        if data["total"] >= _MIN_NETWORK_PARTICIPANTS:
            regions_out[region] = data
        else:
            suppressed_regions.append(region)

    _audit(db, current_user, "market_intelligence_view", "market_intelligence_by_region")
    return {
        "generated_at": _utcnow().isoformat(),
        "regions": regions_out,
        "suppressed_regions": suppressed_regions,
        "k_anonymity_floor": _MIN_NETWORK_PARTICIPANTS,
        "disclaimer": "Per-region anonymized aggregates; regions below the "
                      "k-anonymity floor are suppressed. No regulatory claims.",
    }


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
