"""P15: National SPD Intelligence Network — instrument registry routes."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id, require_enterprise_auth
from app.services.instrument_registry_service import (
    get_defect_history,
    get_registry_stats,
    lookup_instrument,
    register_instrument,
    search_registry,
)

router = APIRouter(prefix="/api/network/registry", tags=["instrument-registry"])


@router.get("/lookup")
def lookup(
    request: Request,
    udi: str | None = Query(default=None),
    barcode: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Lookup instrument by UDI or barcode (requires auth)."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    result = lookup_instrument(db, udi=udi, barcode=barcode)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.registry_lookup",
        resource_type="registry_instrument",
        resource_id=udi or barcode or "unknown",
        details={"udi": udi, "barcode": barcode},
    )

    return {"status": "success", "instrument": result}


@router.post("")
def register(
    request: Request,
    instrument_data: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Register instrument in the national registry (requires auth)."""
    auth = require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    result = register_instrument(db, instrument_data)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=auth.actor_email if hasattr(auth, "actor_email") else "unknown",
        actor_role=auth.role if hasattr(auth, "role") else "",
        action_type="network.registry_register",
        resource_type="registry_instrument",
        resource_id=instrument_data.get("udi", "new"),
        details={"manufacturer": instrument_data.get("manufacturer_name")},
    )

    return {"status": "success", "instrument": result}


@router.get("/stats")
def stats(request: Request, db: Session = Depends(get_db)):
    """Registry size and coverage stats."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    s = get_registry_stats(db)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.registry_stats_viewed",
        resource_type="registry_stats",
        resource_id="all",
    )

    return {"status": "success", "stats": s}


@router.get("/search")
def search(
    request: Request,
    q: str = Query(default=""),
    category: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Search registry by name or manufacturer."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    results = search_registry(db, query=q, category=category)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.registry_search",
        resource_type="registry_instruments",
        resource_id=q or "all",
        details={"query": q, "category": category},
    )

    return {"status": "success", "results": results, "count": len(results)}


@router.get("/{udi}/defect-history")
def defect_history(udi: str, request: Request, db: Session = Depends(get_db)):
    """Aggregated defect history for UDI — no facility IDs."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    history = get_defect_history(db, udi)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.defect_history_viewed",
        resource_type="registry_instrument",
        resource_id=udi,
    )

    return {"status": "success", "defect_history": history}
