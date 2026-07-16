"""P15: National SPD Intelligence Network — benchmarking routes."""
from __future__ import annotations

import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id, require_enterprise_auth
from app.models.network_benchmark import NetworkParticipant
from app.services.network_benchmark_service import (
    METRICS,
    compute_industry_benchmarks,
    get_tenant_percentile,
)

router = APIRouter(prefix="/api/network", tags=["network-benchmarks"])


def _get_or_create_pseudonym(tenant_id: str) -> str:
    month_salt = datetime.utcnow().strftime("%Y-%m")
    digest = hashlib.sha256(f"{tenant_id}{month_salt}".encode()).hexdigest()
    return digest[:12]


def _require_participant(db: Session, tenant_id: str) -> NetworkParticipant:
    participant = (
        db.query(NetworkParticipant)
        .filter(NetworkParticipant.tenant_id == tenant_id, NetworkParticipant.is_active == True)  # noqa: E712
        .first()
    )
    if not participant:
        raise HTTPException(
            status_code=403,
            detail="Network participation required. Please opt in via POST /api/network/opt-in.",
        )
    return participant


@router.post("/opt-in")
def opt_in(request: Request, db: Session = Depends(get_db)):
    """Opt tenant into the national intelligence network."""
    auth = require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    existing = db.query(NetworkParticipant).filter(NetworkParticipant.tenant_id == tenant_id).first()
    if existing and existing.is_active:
        return {"status": "already_active", "pseudonym": existing.pseudonym, "tenant_id": None}

    pseudonym = _get_or_create_pseudonym(tenant_id)

    if existing:
        existing.is_active = True
        existing.opted_out_at = None
        existing.pseudonym = pseudonym
        db.commit()
        db.refresh(existing)
        participant = existing
    else:
        participant = NetworkParticipant(
            tenant_id=tenant_id,
            pseudonym=pseudonym,
            participation_tier="contributor",
            is_active=True,
        )
        db.add(participant)
        db.commit()
        db.refresh(participant)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=auth.actor_email if hasattr(auth, "actor_email") else "unknown",
        actor_role=auth.role if hasattr(auth, "role") else "",
        action_type="network.opt_in",
        resource_type="network_participant",
        resource_id=str(participant.id),
        details={"participation_tier": participant.participation_tier},
    )

    return {
        "status": "success",
        "message": "Successfully opted into the National SPD Intelligence Network",
        "pseudonym": participant.pseudonym,
        "participation_tier": participant.participation_tier,
        "tenant_id": None,  # never expose raw tenant_id in response
    }


@router.get("/opt-in/status")
def opt_in_status(request: Request, db: Session = Depends(get_db)):
    """Get participation status for this tenant."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    participant = db.query(NetworkParticipant).filter(NetworkParticipant.tenant_id == tenant_id).first()
    if not participant:
        return {"is_active": False, "participation_tier": None, "opted_in_at": None}

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.opt_in_status_check",
        resource_type="network_participant",
        resource_id=str(participant.id),
    )

    return {
        "is_active": participant.is_active,
        "participation_tier": participant.participation_tier,
        "opted_in_at": participant.opted_in_at.isoformat() if participant.opted_in_at else None,
        "opted_out_at": participant.opted_out_at.isoformat() if participant.opted_out_at else None,
        "pseudonym": participant.pseudonym,
        "tenant_id": None,  # never expose raw tenant_id
    }


@router.post("/opt-out")
def opt_out(request: Request, db: Session = Depends(get_db)):
    """Opt tenant out of the network."""
    auth = require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    participant = db.query(NetworkParticipant).filter(NetworkParticipant.tenant_id == tenant_id).first()
    if not participant or not participant.is_active:
        return {"status": "not_active", "message": "Tenant was not an active participant"}

    participant.is_active = False
    participant.opted_out_at = datetime.utcnow()
    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=auth.actor_email if hasattr(auth, "actor_email") else "unknown",
        actor_role=auth.role if hasattr(auth, "role") else "",
        action_type="network.opt_out",
        resource_type="network_participant",
        resource_id=str(participant.id),
        details={"opted_out_at": participant.opted_out_at.isoformat()},
    )

    return {
        "status": "success",
        "message": "Successfully opted out. Data will be deleted within 30 days per exit rights.",
        "opted_out_at": participant.opted_out_at.isoformat(),
    }


@router.get("/benchmarks")
def get_benchmarks(request: Request, db: Session = Depends(get_db)):
    """Return current industry benchmarks (requires network participation)."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)
    _require_participant(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.benchmarks_viewed",
        resource_type="industry_benchmarks",
        resource_id="all",
    )

    benchmarks = compute_industry_benchmarks(db)
    participant_count = db.query(NetworkParticipant).filter(NetworkParticipant.is_active == True).count()  # noqa: E712
    any_insufficient = any(b.get("data_source") == "insufficient_data" for b in benchmarks)

    return {
        "status": "success",
        "benchmarks": benchmarks,
        "network_participant_count": participant_count,
        "note": (
            "Some or all of these metrics have insufficient data (see each entry's data_source) -- no real "
            "cross-organization benchmark has been computed for them yet, so no value is reported rather than "
            "an estimated one. Metrics marked data_source='real' include differential privacy noise; cohorts "
            "with N<5 are suppressed."
            if any_insufficient else
            "All values include differential privacy noise. Cohorts with N<5 suppressed."
        ),
    }


@router.get("/benchmarks/my-percentile")
def my_percentile(request: Request, db: Session = Depends(get_db)):
    """Return this tenant's percentile rank per metric."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)
    _require_participant(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.my_percentile_viewed",
        resource_type="industry_benchmarks",
        resource_id="percentile",
    )

    percentiles = [get_tenant_percentile(db, tenant_id, m) for m in METRICS]
    return {
        "status": "success",
        "percentiles": percentiles,
        "tenant_id": None,  # never expose
    }


@router.get("/participants/count")
def participant_count(db: Session = Depends(get_db)):
    """Public endpoint — shows network size without revealing participant identities."""
    count = db.query(NetworkParticipant).filter(NetworkParticipant.is_active == True).count()  # noqa: E712
    return {
        "active_participants": count,
        "note": "Participant identities are anonymized and never exposed.",
    }
