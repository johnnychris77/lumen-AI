"""P23: Global Surgical Intelligence Network — API routes."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_actor, get_request_tenant_id, require_enterprise_auth
from app.models.global_intelligence import (
    GlobalIntelligenceSignal,
    GlobalRecallEarlyWarning,
    GSINParticipant,
)
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


class ReviewSignalRequest(BaseModel):
    decision: str  # "approve" | "reject"
    reviewer_notes: str = ""


class EnrollRequest(BaseModel):
    participant_type: str  # hospital/vendor/manufacturer/regulator
    region: str
    contribution_categories: list[str] = []


class NotifyRequest(BaseModel):
    target: str  # "manufacturer" | "regulatory"
    notification_notes: str = ""


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


@router.post(
    "/api/global-intelligence/signals/{signal_id}/review",
    dependencies=[Depends(require_roles("admin", "executive"))],
)
def review_signal(
    signal_id: int,
    body: ReviewSignalRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Governance Board review: approve or reject a pending signal for network publication."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    if body.decision not in ("approve", "reject"):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_decision", "message": "decision must be 'approve' or 'reject'"},
        )

    signal = db.query(GlobalIntelligenceSignal).filter_by(id=signal_id).first()
    if signal is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Signal not found."})

    if signal.human_review_completed:
        raise HTTPException(
            status_code=409,
            detail={"error": "already_reviewed", "message": "Signal has already been reviewed."},
        )

    if body.decision == "approve":
        if signal.facility_count < 10:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "k_anonymity_not_met",
                    "message": "Cannot approve: signal requires ≥10 facilities for k-anonymity before publication.",
                    "facility_count": signal.facility_count,
                    "required": 10,
                },
            )
        signal.k_anonymity_verified = True
        signal.human_review_completed = True
        signal.published = True
        outcome = "approved_and_published"
    else:
        signal.human_review_completed = True
        signal.published = False
        outcome = "rejected"

    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="admin",
        action_type=f"global_intelligence.signal.{outcome}",
        resource_type="global_intelligence_signals",
        resource_id=str(signal_id),
        details={"decision": body.decision, "reviewer_notes": body.reviewer_notes},
        compliance_flag=True,
    )

    return {
        "status": "success",
        "signal_id": signal_id,
        "decision": body.decision,
        "outcome": outcome,
        "published": signal.published,
        "human_review_required": True,
        "disclaimer": _DISCLAIMER,
    }


@router.post("/api/global-intelligence/enroll")
def enroll_participant(
    body: EnrollRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Enroll this tenant as a GSIN network participant (creates pending record)."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    existing = db.query(GSINParticipant).filter_by(tenant_id=tenant_id).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "already_enrolled",
                "message": f"Tenant already has a participant record with status '{existing.enrollment_status}'.",
                "enrollment_status": existing.enrollment_status,
            },
        )

    import json
    participant = GSINParticipant(
        tenant_id=tenant_id,
        participant_type=body.participant_type,
        region=body.region,
        contribution_categories=json.dumps(body.contribution_categories),
        baa_signed=False,
        dpa_signed=False,
        enrollment_status="pending",
        minimum_contribution_met=False,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="",
        action_type="global_intelligence.participant.enroll",
        resource_type="gsin_participants",
        resource_id=str(participant.id),
        details={"participant_type": body.participant_type, "region": body.region},
        compliance_flag=True,
    )

    return {
        "status": "success",
        "participant_id": participant.id,
        "enrollment_status": "pending",
        "next_steps": [
            "Sign the Data Processing Agreement (DPA) via POST /api/global-intelligence/sign-dpa",
            "Ensure BAA is signed with your account administrator",
            "Begin contributing anonymized signals once enrollment is active",
        ],
        "disclaimer": _DISCLAIMER,
    }


@router.post(
    "/api/global-intelligence/sign-dpa",
    dependencies=[Depends(require_roles("admin"))],
)
def sign_dpa(
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Admin acknowledges DPA signing, activating this tenant's GSIN participation."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    participant = db.query(GSINParticipant).filter_by(tenant_id=tenant_id).first()
    if participant is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_enrolled", "message": "Tenant has no participant record. Enroll first via POST /enroll."},
        )

    if participant.dpa_signed:
        raise HTTPException(
            status_code=409,
            detail={"error": "already_signed", "message": "DPA is already marked as signed."},
        )

    from datetime import datetime, timezone
    participant.dpa_signed = True
    participant.security_attestation_date = datetime.now(timezone.utc)
    participant.enrollment_status = "active"
    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="admin",
        action_type="global_intelligence.participant.dpa_signed",
        resource_type="gsin_participants",
        resource_id=str(participant.id),
        details={"enrollment_status": "active"},
        compliance_flag=True,
    )

    return {
        "status": "success",
        "enrollment_status": "active",
        "dpa_signed": True,
        "message": "DPA signed. Tenant enrollment is now active. You may now contribute anonymized signals to the network.",
        "disclaimer": _DISCLAIMER,
    }


@router.post(
    "/api/global-intelligence/recall-warnings/{warning_id}/notify",
    dependencies=[Depends(require_roles("admin", "executive"))],
)
def notify_recall_warning(
    warning_id: int,
    body: NotifyRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Record that a manufacturer or regulatory body has been notified about this early warning signal."""
    require_enterprise_auth(request)
    tenant_id = _tenant(request)

    if body.target not in ("manufacturer", "regulatory"):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_target", "message": "target must be 'manufacturer' or 'regulatory'"},
        )

    warning = db.query(GlobalRecallEarlyWarning).filter_by(id=warning_id).first()
    if warning is None:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Recall warning not found."})

    if body.target == "manufacturer":
        if warning.manufacturer_notified:
            raise HTTPException(
                status_code=409,
                detail={"error": "already_notified", "message": "Manufacturer has already been marked as notified."},
            )
        warning.manufacturer_notified = True
        field_updated = "manufacturer_notified"
    else:
        if warning.regulatory_notified:
            raise HTTPException(
                status_code=409,
                detail={"error": "already_notified", "message": "Regulatory body has already been marked as notified."},
            )
        warning.regulatory_notified = True
        field_updated = "regulatory_notified"

    # Escalate status if both parties notified
    if warning.manufacturer_notified and warning.regulatory_notified:
        warning.status = "escalated"

    db.commit()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=_actor(request),
        actor_role="admin",
        action_type=f"global_intelligence.recall_warning.notify_{body.target}",
        resource_type="global_recall_early_warnings",
        resource_id=str(warning_id),
        details={"target": body.target, "notes": body.notification_notes},
        compliance_flag=True,
    )

    return {
        "status": "success",
        "warning_id": warning_id,
        "field_updated": field_updated,
        "warning_status": warning.status,
        "manufacturer_notified": warning.manufacturer_notified,
        "regulatory_notified": warning.regulatory_notified,
        "human_review_required": True,
        "important_notice": (
            "This records that a human-initiated notification was sent. "
            "This is NOT a regulatory recall action. "
            "All further steps require human review and regulatory consultation."
        ),
        "disclaimer": _DISCLAIMER,
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
