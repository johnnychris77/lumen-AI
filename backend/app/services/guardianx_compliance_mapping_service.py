"""v5.2 — Project GuardianX, Section 7: Compliance Mapping.

Apollo's `regulatory_standards_catalogue.py` (v4.7) already catalogues
AAMI/AORN/Joint Commission/DNV standard references and maps *clinical
findings* to them (`MappingDef`). `ComplianceCapabilityMapping` maps a
*platform capability* to an organizational requirement instead --
genuinely different from a finding→clause mapping. When
`requirement_type` is `aami` or `aorn`, the mapping is checked against
the existing catalogue's real standard codes and flagged
`verified_against_catalogue` -- never silently assumed.

"The platform stores references and supports traceability rather than
claiming regulatory certification": nothing in this module (or its
routes) ever returns a certification/clearance claim.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.guardianx_assurance import REQUIREMENT_TYPES, ComplianceCapabilityMapping
from app.services.regulatory_standards_catalogue import get_standards


class UnknownComplianceMappingError(Exception):
    pass


def _catalogue_codes_for_body(body_prefix: str) -> set[str]:
    return {s.code for s in get_standards() if s.body.startswith(body_prefix)}


def _to_dict(row: ComplianceCapabilityMapping) -> dict:
    verified = False
    if row.requirement_type == "aami":
        verified = row.requirement_reference in _catalogue_codes_for_body("aami")
    elif row.requirement_type == "aorn":
        verified = row.requirement_reference in _catalogue_codes_for_body("aorn")
    return {
        "id": row.id,
        "capability_name": row.capability_name,
        "capability_description": row.capability_description,
        "requirement_type": row.requirement_type,
        "requirement_reference": row.requirement_reference,
        "traceability_notes": row.traceability_notes,
        "mapped_by": row.mapped_by,
        "verified_against_catalogue": verified,
        "created_at": row.created_at.isoformat(),
    }


def create_mapping(
    db: Session, *, capability_name: str, capability_description: str = "", requirement_type: str,
    requirement_reference: str, traceability_notes: str = "", mapped_by: str = "",
) -> dict:
    if requirement_type not in REQUIREMENT_TYPES:
        raise ValueError(f"requirement_type must be one of {REQUIREMENT_TYPES}")
    row = ComplianceCapabilityMapping(
        capability_name=capability_name, capability_description=capability_description,
        requirement_type=requirement_type, requirement_reference=requirement_reference,
        traceability_notes=traceability_notes, mapped_by=mapped_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def _get_or_404(db: Session, mapping_id: int) -> ComplianceCapabilityMapping:
    row = db.query(ComplianceCapabilityMapping).filter(ComplianceCapabilityMapping.id == mapping_id).first()
    if row is None:
        raise UnknownComplianceMappingError(f"Compliance mapping {mapping_id} not found.")
    return row


def get_mapping(db: Session, mapping_id: int) -> dict:
    return _to_dict(_get_or_404(db, mapping_id))


def list_mappings(db: Session, *, capability_name: str = "", requirement_type: str = "") -> list[dict]:
    query = db.query(ComplianceCapabilityMapping)
    if capability_name:
        query = query.filter(ComplianceCapabilityMapping.capability_name == capability_name)
    if requirement_type:
        if requirement_type not in REQUIREMENT_TYPES:
            raise ValueError(f"requirement_type must be one of {REQUIREMENT_TYPES}")
        query = query.filter(ComplianceCapabilityMapping.requirement_type == requirement_type)
    rows = query.order_by(ComplianceCapabilityMapping.created_at.desc()).all()
    return [_to_dict(r) for r in rows]


def traceability_matrix(db: Session) -> dict:
    rows = db.query(ComplianceCapabilityMapping).all()
    by_capability: dict[str, list[dict]] = {}
    for r in rows:
        by_capability.setdefault(r.capability_name, []).append(_to_dict(r))
    return {"capability_count": len(by_capability), "by_capability": by_capability}
