"""v1.9 — Pilot Site Configuration (Deliverable 4)."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.pilot_config import PilotSiteConfig


def _load(text: str) -> list[str]:
    try:
        return json.loads(text or "[]")
    except (TypeError, ValueError):
        return []


def config_to_dict(row: PilotSiteConfig) -> dict:
    return {
        "tenant_id": row.tenant_id,
        "facility_name": row.facility_name,
        "department": row.department,
        "enabled_instrument_families": _load(row.enabled_instrument_families),
        "required_inspection_zones": _load(row.required_inspection_zones),
        "baseline_required": row.baseline_required,
        "minimum_coverage_pct": row.minimum_coverage_pct,
        "supervisor_review_threshold_score": row.supervisor_review_threshold_score,
        "updated_by": row.updated_by,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_or_create_config(db: Session, tenant_id: str) -> PilotSiteConfig:
    """A pilot site always has a config — defaults are conservative
    (baseline required, 75% coverage, review at/below 70) rather than the
    absence of a row meaning "no rules apply"."""
    row = db.query(PilotSiteConfig).filter(PilotSiteConfig.tenant_id == tenant_id).first()
    if row is None:
        row = PilotSiteConfig(tenant_id=tenant_id)
        db.add(row)
        db.flush()
    return row


def update_config(
    db: Session, tenant_id: str, *, updated_by: str, facility_name: str | None = None,
    department: str | None = None, enabled_instrument_families: list[str] | None = None,
    required_inspection_zones: list[str] | None = None, baseline_required: bool | None = None,
    minimum_coverage_pct: int | None = None, supervisor_review_threshold_score: int | None = None,
) -> PilotSiteConfig:
    row = get_or_create_config(db, tenant_id)
    if facility_name is not None:
        row.facility_name = facility_name
    if department is not None:
        row.department = department
    if enabled_instrument_families is not None:
        row.enabled_instrument_families = json.dumps(enabled_instrument_families)
    if required_inspection_zones is not None:
        row.required_inspection_zones = json.dumps(required_inspection_zones)
    if baseline_required is not None:
        row.baseline_required = baseline_required
    if minimum_coverage_pct is not None:
        row.minimum_coverage_pct = minimum_coverage_pct
    if supervisor_review_threshold_score is not None:
        row.supervisor_review_threshold_score = supervisor_review_threshold_score
    row.updated_by = updated_by
    return row
