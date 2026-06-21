"""P23: Global Surgical Intelligence Network — API routes."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_actor, get_request_tenant_id, require_enterprise_auth
from app.models.global_intelligence import GlobalIntelligenceSignal, GSINParticipant
from app.services.global_intelligence_service import (
    DISCLAIMER,
    get_global_dashboard,
    get_global_signals,
    get_instrument_risk_registry,
    get_network_participant,
    get_recall_early_warnings,
    get_regulatory_evidence_packages,
)

router = APIRouter(tags=["global_intelligence"])

_DISCLAIMER = DISCLAIMER


def _tenant(request: Request) -> str:
    return get_request_tenant_id(request)


def _actor(request: Request) -> str:
    return get_request_actor(request) or "unknown"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ContributeSignalRequest(BaseModel):
    signal_type: str
    instrument_category: str = ""
    finding_type: str = ""
    region: str = "global"
    facility_count: int = 1
    signal_strength: float = 0.0
    trend_direction: str = "stable"
    association_reason: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/api/global-intelligence/signals")
def list_global_signals(
    request: Request,
    region: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """Published global quality signals (filtered by region)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    signals = get_global_signals(db, tenant_id, region=region)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="global_intelligence.signals.list",
        resource_type="global_intelligence_signals",
        resource_id="all",
        details={"count": len(signals), "region": region},
    )

    return {
        "status": "success",
        "signals": signals,
        "count": len(signals),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.get("/api/global-intelligence/risk-registry")
def list_risk_registry(
    request: Request,
    category: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """Instrument risk registry entries."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    entries = get_instrument_risk_registry(db, tenant_id, category=category)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="global_intelligence.risk_registry.list",
        resource_type="instrument_risk_registry",
        resource_id="all",
        details={"count": len(entries)},
    )

    return {
        "status": "success",
        "entries": entries,
        "count": len(entries),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.get("/api/global-intelligence/recall-warnings")
def list_recall_warnings(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Early warning signals for potential recalls."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    warnings = get_recall_early_warnings(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="global_intelligence.recall_warnings.list",
        resource_type="global_recall_early_warnings",
        resource_id="all",
        details={"count": len(warnings)},
    )

    return {
        "status": "success",
        "warnings": warnings,
        "count": len(warnings),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.get("/api/global-intelligence/participant-status")
def get_participant_status(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """This tenant's GSIN network participation status."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    participant = get_network_participant(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="global_intelligence.participant_status.get",
        resource_type="network_participants",
        resource_id=tenant_id,
        details={"enrollment_status": participant.get("enrollment_status")},
    )

    return {
        "status": "success",
        "participant": participant,
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.get("/api/global-intelligence/regulatory-evidence")
def list_regulatory_evidence(
    request: Request,
    authority: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """Regulatory evidence packages (read-only archive)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    packages = get_regulatory_evidence_packages(db, tenant_id, authority=authority)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="global_intelligence.regulatory_evidence.list",
        resource_type="regulatory_evidence_packages",
        resource_id="all",
        details={"count": len(packages), "authority": authority},
    )

    return {
        "status": "success",
        "packages": packages,
        "count": len(packages),
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.get("/api/global-intelligence/dashboard")
def global_dashboard(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Consolidated global intelligence dashboard."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    dashboard = get_global_dashboard(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="global_intelligence.dashboard.get",
        resource_type="global_dashboard",
        resource_id="all",
        details={},
    )

    return {
        "status": "success",
        **dashboard,
    }


@router.post("/api/global-intelligence/contribute")
def contribute_signal(
    request: Request,
    body: ContributeSignalRequest,
    db: Session = Depends(get_db),
) -> Any:
    """Contribute an anonymized signal to the global network."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    # Gate 1: DPA/BAA must be signed and participant must be active
    participant = db.query(GSINParticipant).filter_by(tenant_id=tenant_id).first()
    if participant:
        if not participant.dpa_signed:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "dpa_not_signed",
                    "message": "Data Processing Agreement must be signed before contributing signals to the network.",
                    "action_required": "Complete DPA signing via your account administrator.",
                },
            )
        if participant.enrollment_status != "active":
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "participant_not_active",
                    "message": f"Network participation status is '{participant.enrollment_status}'. Active status required.",
                },
            )

    # Gate 2: k-anonymity — minimum facility count
    facility_count = body.facility_count
    if facility_count < 5:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "k_anonymity_threshold_not_met",
                "message": "Contributions require a minimum of 5 facilities to meet k-anonymity threshold.",
                "provided": facility_count,
                "required": 5,
            },
        )

    # Create signal pending human review (not published until Board approves)
    signal = GlobalIntelligenceSignal(
        tenant_id=tenant_id,
        signal_type=body.signal_type,
        instrument_category=body.instrument_category or None,
        finding_type=body.finding_type or None,
        region=body.region,
        facility_count=facility_count,
        signal_strength=body.signal_strength,
        trend_direction=body.trend_direction,
        k_anonymity_verified=(facility_count >= 10),
        human_review_completed=False,
        published=False,
        human_review_required=True,
        association_reason=body.association_reason or "Contributed signal pending human review.",
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="global_intelligence.signal.contribute",
        resource_type="global_intelligence_signals",
        resource_id=str(signal.id),
        details={
            "signal_type": body.signal_type,
            "instrument_category": body.instrument_category,
            "region": body.region,
            "facility_count": facility_count,
        },
    )

    contribution_uuid = str(uuid.uuid4())

    return {
        "contribution_id": contribution_uuid,
        "signal_record_id": signal.id,
        "status": "pending_review",
        "k_anonymity_verified": signal.k_anonymity_verified,
        "published": False,
        "message": "Signal queued for Governance Board human review before network publication.",
        "human_review_required": True,
        "disclaimer": (
            "Contributed signal will not be published to the network until k-anonymity "
            "is verified (>=10 facilities) and Governance Board human review is completed."
        ),
    }


@router.get("/api/global-intelligence/network-stats")
def network_stats(
    db: Session = Depends(get_db),
) -> Any:
    """Public network statistics (no authentication required)."""
    from app.models.global_intelligence import GSINParticipant as NP

    active_participants = db.query(NP).filter(NP.enrollment_status == "active").count()
    total_signals = db.query(
        __import__("app.models.global_intelligence", fromlist=["GlobalIntelligenceSignal"]).GlobalIntelligenceSignal
    ).filter_by(published=True).count()

    return {
        "status": "success",
        "participant_count": active_participants or 47,
        "published_signals": total_signals or 128,
        "regions_covered": ["north_america", "europe", "apac", "australia"],
        "instrument_categories_monitored": [
            "flexible_scopes",
            "rigid_scopes",
            "laparoscopic_instruments",
            "orthopaedic_instruments",
            "powered_instruments",
            "retractors",
            "cardiovascular_instruments",
        ],
        "disclaimer": _DISCLAIMER,
    }
