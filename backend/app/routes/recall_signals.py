"""P15: National SPD Intelligence Network — recall signal routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id, require_enterprise_auth
from app.models.network_benchmark import NetworkParticipant
from app.services.recall_signal_engine import (
    escalate_signal,
    get_active_signals,
    get_signals_for_tenant,
)

router = APIRouter(prefix="/api/network/recall-signals", tags=["recall-signals"])


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


@router.get("")
def list_signals(request: Request, db: Session = Depends(get_db)):
    """List active recall signals (requires network participation)."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)
    _require_participant(db, tenant_id)

    signals = get_active_signals(db)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.recall_signals_viewed",
        resource_type="recall_signals",
        resource_id="all",
        details={"signal_count": len(signals)},
    )

    return {
        "status": "success",
        "signals": signals,
        "count": len(signals),
        "note": "All facility identifiers are anonymized. N<3 signals suppressed.",
    }


@router.get("/my-exposure")
def my_exposure(request: Request, db: Session = Depends(get_db)):
    """Signals affecting this tenant's instrument types."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)
    _require_participant(db, tenant_id)

    signals = get_signals_for_tenant(db, tenant_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.my_exposure_viewed",
        resource_type="recall_signals",
        resource_id="exposure",
        details={"signal_count": len(signals)},
    )

    return {
        "status": "success",
        "signals": signals,
        "count": len(signals),
        "tenant_id": None,  # never expose
    }


@router.get("/{signal_id}")
def signal_detail(signal_id: str, request: Request, db: Session = Depends(get_db)):
    """Get detail for a specific recall signal."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)
    _require_participant(db, tenant_id)

    all_signals = get_active_signals(db)
    sig = next((s for s in all_signals if s["signal_id"] == signal_id), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.recall_signal_detail_viewed",
        resource_type="recall_signal",
        resource_id=signal_id,
    )

    return {"status": "success", "signal": sig}


@router.post("/{signal_id}/escalate")
def escalate(signal_id: str, request: Request, db: Session = Depends(get_db)):
    """Escalate signal to FDA (requires auth)."""
    auth = require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    result = escalate_signal(db, signal_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=auth.actor_email if hasattr(auth, "actor_email") else "unknown",
        actor_role=auth.role if hasattr(auth, "role") else "",
        action_type="network.recall_signal_escalated_to_fda",
        resource_type="recall_signal",
        resource_id=signal_id,
        compliance_flag=True,
        details={"escalated_by_pseudonym": None},  # anonymized
    )

    return {"status": "success", "result": result}
