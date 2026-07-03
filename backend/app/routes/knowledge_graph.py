"""Phase 21 — SPD Clinical Knowledge Graph & Clinical Reasoning Engine routes.

Route: /knowledge-graph (frontend). API prefix below.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.services.instrument_family_profiles import INSTRUMENT_FAMILY_PROFILES
from app.services.knowledge_graph_service import (
    enterprise_knowledge_analytics,
    explain_inspection,
    explore,
    get_instrument_family_intelligence,
    graph_schema,
    learning_confidence,
    list_instrument_family_intelligence,
    reasoning_chain,
)

router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])

_READ_ROLES = ("admin", "spd_manager", "operator", "viewer")


@router.get("/schema")
def get_graph_schema(current_user=Depends(require_roles(*_READ_ROLES))):
    """Section 1 — node/relationship taxonomy."""
    return graph_schema()


@router.get("/instrument-families")
def get_instrument_families(current_user=Depends(require_roles(*_READ_ROLES))):
    """Section 3 — all ten instrument family knowledge profiles."""
    return {"families": list_instrument_family_intelligence()}


@router.get("/instrument-families/{family_key}")
def get_instrument_family(family_key: str, current_user=Depends(require_roles(*_READ_ROLES))):
    profile = get_instrument_family_intelligence(family_key)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown instrument family '{family_key}'. Known families: {sorted(INSTRUMENT_FAMILY_PROFILES)}",
        )
    return profile


@router.get("/reasoning-chain")
def get_reasoning_chain(
    instrument_type: str = Query(...),
    finding_type: str = Query(...),
    manufacturer: str = Query(""),
    model: str = Query(""),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 2/5 — the traceable clinical reasoning chain."""
    return reasoning_chain(instrument_type, finding_type, manufacturer, model)


@router.get("/explain/{inspection_id}")
def get_explainability_graph(
    inspection_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 6 — the "Why?" explainability graph for one real inspection."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return explain_inspection(db, insp)


@router.get("/explore")
def get_explorer(
    category: str = Query(..., description="manufacturer|instrument|model|finding|zone|failure_mode|recommendation|supervisor_learning"),
    q: str = Query("", description="Optional search text"),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_READ_ROLES)),
):
    """Section 7 — Knowledge Graph Explorer."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    return explore(db, tenant_id, category, q)


@router.get("/analytics")
def get_enterprise_analytics(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Section 8 — Enterprise Knowledge Analytics."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    return enterprise_knowledge_analytics(db, tenant_id)


@router.get("/learning-confidence")
def get_learning_confidence(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Section 9 — Continuous Knowledge Learning confidence signals."""
    tenant_id = getattr(current_user, "tenant_id", None) or "default-tenant"
    return learning_confidence(db, tenant_id)
