"""v5.3 — Project Genesis AI, Section 1: Global Instrument Registry.

P15's `RegistryInstrument` (`instrument_registry_service.py`) already is
the world-scale, network-aggregate instrument registry — this module
only manages the new columns Genesis AI added (family, IFU versions,
anatomy profile link, inspection zones, Digital Twin/baseline template
references, failure modes, repair guidance, knowledge references). It
never touches `instrument_registry_service.py`'s existing functions or
its seeded-mock-fallback behavior, and it never fabricates a profile for
an instrument that doesn't have a real `RegistryInstrument` row.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.instrument_registry import RegistryInstrument


class UnknownRegistryInstrumentError(Exception):
    pass


def _get_or_404(db: Session, instrument_id: int) -> RegistryInstrument:
    row = db.query(RegistryInstrument).filter(RegistryInstrument.id == instrument_id).first()
    if row is None:
        raise UnknownRegistryInstrumentError(f"Registry instrument {instrument_id} not found.")
    return row


def _profile_dict(row: RegistryInstrument) -> dict:
    return {
        "id": row.id,
        "udi": row.udi,
        "manufacturer_name": row.manufacturer_name,
        "model_name": row.model_name,
        "instrument_category": row.instrument_category,
        "instrument_family": row.instrument_family,
        "ifu_versions": json.loads(row.ifu_versions_json or "[]"),
        "anatomy_profile_id": row.anatomy_profile_id,
        "inspection_zones": json.loads(row.inspection_zones_json or "[]"),
        "digital_twin_template_ref": row.digital_twin_template_ref,
        "baseline_template_ref": row.baseline_template_ref,
        "failure_modes": json.loads(row.failure_modes_json or "[]"),
        "repair_guidance": row.repair_guidance,
        "knowledge_references": json.loads(row.knowledge_references_json or "[]"),
    }


def set_instrument_profile(
    db: Session, instrument_id: int, *, instrument_family: str | None = None,
    ifu_versions: list[str] | None = None, anatomy_profile_id: int | None = None,
    inspection_zones: list[str] | None = None, digital_twin_template_ref: str | None = None,
    baseline_template_ref: str | None = None, failure_modes: list[str] | None = None,
    repair_guidance: str | None = None, knowledge_references: list[str] | None = None,
) -> dict:
    row = _get_or_404(db, instrument_id)
    if instrument_family is not None:
        row.instrument_family = instrument_family
    if ifu_versions is not None:
        row.ifu_versions_json = json.dumps(ifu_versions)
    if anatomy_profile_id is not None:
        row.anatomy_profile_id = anatomy_profile_id
    if inspection_zones is not None:
        row.inspection_zones_json = json.dumps(inspection_zones)
    if digital_twin_template_ref is not None:
        row.digital_twin_template_ref = digital_twin_template_ref
    if baseline_template_ref is not None:
        row.baseline_template_ref = baseline_template_ref
    if failure_modes is not None:
        row.failure_modes_json = json.dumps(failure_modes)
    if repair_guidance is not None:
        row.repair_guidance = repair_guidance
    if knowledge_references is not None:
        row.knowledge_references_json = json.dumps(knowledge_references)
    db.commit()
    db.refresh(row)
    return _profile_dict(row)


def get_instrument_profile(db: Session, instrument_id: int) -> dict:
    return _profile_dict(_get_or_404(db, instrument_id))


def list_instruments_by_family(db: Session, instrument_family: str) -> list[dict]:
    rows = db.query(RegistryInstrument).filter(RegistryInstrument.instrument_family == instrument_family).all()
    return [_profile_dict(r) for r in rows]
