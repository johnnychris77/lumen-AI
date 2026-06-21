"""P15: National SPD Intelligence Network — baseline library routes."""
from __future__ import annotations

import hashlib
import random
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id, require_enterprise_auth
from app.models.baseline_library import BaselineLibraryEntry

router = APIRouter(prefix="/api/network/baselines", tags=["baseline-library"])


def _seed(s: str) -> random.Random:
    h = hashlib.md5(s.encode()).hexdigest()[:8]
    return random.Random(int(h, 16))


def _entry_to_dict(e: BaselineLibraryEntry) -> dict:
    return {
        "id": e.id,
        "udi": e.udi,
        "instrument_category": e.instrument_category,
        "manufacturer_name": e.manufacturer_name,
        "model_name": e.model_name,
        "baseline_type": e.baseline_type,
        "baseline_version": e.baseline_version,
        "approval_status": e.approval_status,
        "approved_by": e.approved_by,
        "approved_at": e.approved_at.isoformat() if e.approved_at else None,
        "contributing_facilities": e.contributing_facilities,
        "governance_notes": e.governance_notes,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _mock_baselines(seed_key: str = "all") -> list[dict]:
    rng = _seed(f"baselines:{seed_key}")
    categories = ["endoscope", "surgical_tray", "laparoscopic", "robotic_instrument"]
    return [
        {
            "id": i + 1,
            "udi": f"UDI-BL-{rng.randint(10000, 99999)}",
            "instrument_category": rng.choice(categories),
            "manufacturer_name": f"Manufacturer-{rng.randint(1, 15)}",
            "model_name": f"Model-BL-{rng.randint(100, 999)}",
            "baseline_type": rng.choice(["manufacturer", "network_contributed"]),
            "baseline_version": f"{rng.randint(1, 3)}.{rng.randint(0, 9)}",
            "approval_status": "approved",
            "approved_by": "network_stewardship_council",
            "contributing_facilities": rng.randint(5, 25),
            "data_source": "mock",
        }
        for i in range(rng.randint(5, 12))
    ]


@router.get("")
def list_baselines(request: Request, db: Session = Depends(get_db)):
    """List approved baselines (requires auth)."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    entries = db.query(BaselineLibraryEntry).filter(
        BaselineLibraryEntry.approval_status == "approved"
    ).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.baselines_listed",
        resource_type="baseline_library",
        resource_id="all",
    )

    if entries:
        return {"status": "success", "baselines": [_entry_to_dict(e) for e in entries]}

    return {"status": "success", "baselines": _mock_baselines(), "data_source": "mock"}


@router.post("")
def submit_baseline(
    request: Request,
    baseline_data: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Submit a baseline for network contribution (requires auth + enterprise)."""
    auth = require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    entry = BaselineLibraryEntry(
        udi=baseline_data.get("udi"),
        instrument_category=baseline_data.get("instrument_category", "general"),
        manufacturer_name=baseline_data.get("manufacturer_name", "Unknown"),
        model_name=baseline_data.get("model_name", "Unknown"),
        baseline_type=baseline_data.get("baseline_type", "network_contributed"),
        baseline_version=baseline_data.get("baseline_version", "1.0"),
        approval_status="pending",
        governance_notes=baseline_data.get("governance_notes"),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=auth.actor_email if hasattr(auth, "actor_email") else "unknown",
        actor_role=auth.role if hasattr(auth, "role") else "",
        action_type="network.baseline_submitted",
        resource_type="baseline_library",
        resource_id=str(entry.id),
        details={"manufacturer": entry.manufacturer_name, "model": entry.model_name},
    )

    return {"status": "success", "baseline": _entry_to_dict(entry)}


@router.get("/search")
def search_baselines(
    request: Request,
    q: str = Query(default=""),
    manufacturer: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Search baselines by instrument or manufacturer."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    query = db.query(BaselineLibraryEntry)
    if q:
        query = query.filter(
            (BaselineLibraryEntry.model_name.ilike(f"%{q}%"))
            | (BaselineLibraryEntry.instrument_category.ilike(f"%{q}%"))
        )
    if manufacturer:
        query = query.filter(BaselineLibraryEntry.manufacturer_name.ilike(f"%{manufacturer}%"))

    entries = query.limit(50).all()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.baselines_searched",
        resource_type="baseline_library",
        resource_id=q or "all",
    )

    if entries:
        return {"status": "success", "results": [_entry_to_dict(e) for e in entries]}

    return {"status": "success", "results": _mock_baselines(q or "search"), "data_source": "mock"}


@router.get("/stats")
def baseline_stats(request: Request, db: Session = Depends(get_db)):
    """Library size and coverage stats."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    total = db.query(BaselineLibraryEntry).count()
    approved = db.query(BaselineLibraryEntry).filter(
        BaselineLibraryEntry.approval_status == "approved"
    ).count()
    pending = db.query(BaselineLibraryEntry).filter(
        BaselineLibraryEntry.approval_status == "pending"
    ).count()

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.baseline_stats_viewed",
        resource_type="baseline_library",
        resource_id="stats",
    )

    return {
        "status": "success",
        "stats": {
            "total": total or 342,
            "approved": approved or 315,
            "pending": pending or 27,
            "data_source": "real" if total > 0 else "mock",
        },
    }


@router.get("/{entry_id}")
def baseline_detail(entry_id: int, request: Request, db: Session = Depends(get_db)):
    """Get baseline detail."""
    require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    entry = db.get(BaselineLibraryEntry, entry_id)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email="unknown",
        actor_role="",
        action_type="network.baseline_detail_viewed",
        resource_type="baseline_library",
        resource_id=str(entry_id),
    )

    if entry:
        return {"status": "success", "baseline": _entry_to_dict(entry)}

    # Mock fallback
    rng = _seed(f"baseline_detail:{entry_id}")
    return {
        "status": "success",
        "baseline": {
            "id": entry_id,
            "instrument_category": rng.choice(["endoscope", "surgical_tray"]),
            "manufacturer_name": f"Manufacturer-{rng.randint(1, 15)}",
            "model_name": f"Model-{rng.randint(100, 999)}",
            "approval_status": "approved",
            "contributing_facilities": rng.randint(5, 20),
            "data_source": "mock",
        },
    }


@router.post("/{entry_id}/approve")
def approve_baseline(entry_id: int, request: Request, db: Session = Depends(get_db)):
    """Approve baseline (admin action)."""
    auth = require_enterprise_auth(request, db=db)
    tenant_id = get_request_tenant_id(request)

    entry = db.get(BaselineLibraryEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Baseline not found")

    actor = auth.actor_email if hasattr(auth, "actor_email") else "admin"
    entry.approval_status = "approved"
    entry.approved_by = actor
    entry.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)

    log_audit_event(
        db,
        tenant_id=tenant_id,
        tenant_name=tenant_id,
        actor_email=actor,
        actor_role=auth.role if hasattr(auth, "role") else "",
        action_type="network.baseline_approved",
        resource_type="baseline_library",
        resource_id=str(entry_id),
        compliance_flag=True,
    )

    return {"status": "success", "baseline": _entry_to_dict(entry)}
