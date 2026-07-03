"""Phase 15 — anatomy library read, knowledge library CRUD, executive analytics.

- GET  /api/instrument-anatomy/{instrument_type} — resolved anatomy definition.
- POST /api/instrument-knowledge — register a manufacturer/model knowledge entry.
- GET  /api/instrument-knowledge — list entries.
- GET  /api/analytics/zone-intelligence — executive zone/coverage analytics
  computed from real data (stubs return zero/empty until data exists; nothing
  fabricated).
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.instrument_knowledge import InstrumentKnowledge
from app.models.supervisor_review import SupervisorReview
from app.services.instrument_anatomy import anatomy_profile, list_anatomy_families
from app.services.inspection_coverage import coverage_dashboard_summary

router = APIRouter(tags=["instrument-intelligence"])


@router.get("/instrument-anatomy")
def list_instrument_anatomy(
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    """Anatomy Library — every declared instrument-family anatomy definition
    (family, zones, required image views, high-risk zones). Backs the
    Anatomy Library page's browse view."""
    return {"families": list_anatomy_families()}


@router.get("/instrument-anatomy/{instrument_type}")
def instrument_anatomy(
    instrument_type: str,
    manufacturer: str | None = None,
    model: str | None = None,
    instrument_name: str | None = None,
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    """Anatomy Profile Service — resolved profile (family, zones, high-risk zones,
    required image views, per-zone descriptions/risks, manual-check steps). Falls
    back to a generic SPD profile with a supervisor-review warning when unknown."""
    return anatomy_profile(instrument_type, manufacturer, model, instrument_name)


@router.get("/instrument-zones")
def instrument_zone_taxonomy(
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    """Inspection Zones Library — the full zone taxonomy, high-retention zones,
    and per-zone risk/reason/manual-check reference. Backs the Inspection Zones
    library page."""
    from app.services.instrument_zones import HIGH_RETENTION_ZONES, ZONE_INFO, ZONE_TAXONOMY

    return {
        "zone_taxonomy": ZONE_TAXONOMY,
        "high_retention_zones": sorted(HIGH_RETENTION_ZONES),
        "zone_info": ZONE_INFO,
    }


@router.get("/coverage-dashboard/summary")
def coverage_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    """Inspection Coverage Dashboard — real aggregate coverage stats (average
    coverage, status breakdown, most commonly missing zones, per-family
    averages) computed from stored inspections. Nothing fabricated: inspections
    that never had zones tagged are excluded from averages, not counted as 0%."""
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    return coverage_dashboard_summary(db, tenant_id)


class KnowledgeIn(BaseModel):
    manufacturer: str = Field("", max_length=255)
    model: str = Field("", max_length=255)
    instrument_family: str = Field("", max_length=100)
    ifu_reference: str = Field("", max_length=500)
    anatomy_zones: list[str] = Field(default_factory=list)
    high_risk_zones: list[str] = Field(default_factory=list)
    known_failure_modes: list[str] = Field(default_factory=list)
    maintenance_interval: str = Field("", max_length=255)
    repair_criteria: str = Field("", max_length=2000)
    replacement_criteria: str = Field("", max_length=2000)


@router.post("/instrument-knowledge", status_code=201)
def create_knowledge(
    body: KnowledgeIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    row = InstrumentKnowledge(
        tenant_id=tenant_id,
        manufacturer=body.manufacturer, model=body.model,
        instrument_family=body.instrument_family, ifu_reference=body.ifu_reference,
        anatomy_zones=json.dumps(body.anatomy_zones),
        high_risk_zones=json.dumps(body.high_risk_zones),
        known_failure_modes=json.dumps(body.known_failure_modes),
        maintenance_interval=body.maintenance_interval,
        repair_criteria=body.repair_criteria,
        replacement_criteria=body.replacement_criteria,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "manufacturer": row.manufacturer, "model": row.model}


@router.get("/instrument-knowledge")
def list_knowledge(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager", "operator", "viewer")),
):
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    rows = (
        db.query(InstrumentKnowledge)
        .filter(InstrumentKnowledge.tenant_id == tenant_id)
        .order_by(InstrumentKnowledge.id.desc())
        .all()
    )
    return {
        "count": len(rows),
        "entries": [
            {
                "id": r.id, "manufacturer": r.manufacturer, "model": r.model,
                "instrument_family": r.instrument_family, "ifu_reference": r.ifu_reference,
                "anatomy_zones": json.loads(r.anatomy_zones or "[]"),
                "high_risk_zones": json.loads(r.high_risk_zones or "[]"),
                "known_failure_modes": json.loads(r.known_failure_modes or "[]"),
                "maintenance_interval": r.maintenance_interval,
                "repair_criteria": r.repair_criteria,
                "replacement_criteria": r.replacement_criteria,
            }
            for r in rows
        ],
    }


@router.get("/analytics/zone-intelligence")
def zone_intelligence(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles("admin", "spd_manager")),
):
    """Executive zone/coverage analytics — computed from real data only.

    Metrics that require per-zone finding history (contamination/corrosion rate
    by zone) are surfaced as empty until that data is captured, rather than
    fabricated. Supervisor override-by-zone is computed from real reviews.
    """
    tenant_id = getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)
    inspections = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id)
    total = inspections.filter(models.Inspection.has_image.is_(True)).count()

    reviews = db.query(SupervisorReview).filter(SupervisorReview.tenant_id == tenant_id).all()
    override_by_zone: dict[str, int] = {}
    corrected_zone_counts: dict[str, int] = {}
    for r in reviews:
        if r.override_action:
            z = r.corrected_zone or "unspecified"
            override_by_zone[z] = override_by_zone.get(z, 0) + 1
        if r.corrected_zone:
            corrected_zone_counts[r.corrected_zone] = corrected_zone_counts.get(r.corrected_zone, 0) + 1

    return {
        "total_ai_inspections": total,
        # Require per-zone finding capture (future) — not fabricated.
        "most_common_contamination_zones": [],
        "most_frequently_missed_zones": [],
        "highest_risk_instrument_families": [],
        "contamination_rate_by_zone": {},
        "corrosion_rate_by_zone": {},
        "average_inspection_coverage": None,
        "average_images_per_inspection": None,
        # Computed from real supervisor reviews:
        "supervisor_override_by_zone": override_by_zone,
        "supervisor_corrected_zone_counts": corrected_zone_counts,
        "note": (
            "Zone/coverage rates require per-zone finding history (captured going "
            "forward); shown empty rather than fabricated. Override-by-zone is real."
        ),
    }
