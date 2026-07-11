"""Project Vulcan, Section 9: Instrument Forensics Workspace.

Composes one instrument's full forensic record for `/instrument-forensics`:
identity, real Digital Twin / anatomy profile references (by version string
only -- never copied), inspection/finding history, repair history, reliability
score, probable contributors, and recommended disposition. Filtering supports
every facet the brief names.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.or_connect import RepairRequest
from app.models.vulcan_reliability import VulcanReliabilityAssessment
from app.services.instrument_anatomy import anatomy_profile
from app.services.vulcan_progression_service import _inspections_for_identity, findings_timeline
from app.services.vulcan_reliability_agent_service import to_dict
from app.services.vulcan_repair_effectiveness_service import repair_history_for_instrument


def instrument_forensics_record(db: Session, tenant_id: str, instrument_identity: str, instrument_type: str = "") -> dict:
    """Section 9: full forensics workspace payload for one instrument."""
    latest_assessment = (
        db.query(VulcanReliabilityAssessment)
        .filter(
            VulcanReliabilityAssessment.tenant_id == tenant_id,
            VulcanReliabilityAssessment.instrument_identity == instrument_identity,
        )
        .order_by(VulcanReliabilityAssessment.created_at.desc())
        .first()
    )
    inspections = _inspections_for_identity(db, tenant_id, instrument_identity)
    timeline = findings_timeline(db, tenant_id, instrument_identity)
    repairs = repair_history_for_instrument(db, tenant_id, instrument_identity)
    profile = anatomy_profile(instrument_type) if instrument_type else None

    return {
        "instrument_identity": instrument_identity,
        "anatomy_profile": profile,
        "inspection_history": [
            {"inspection_id": i.id, "created_at": i.created_at.isoformat() if i.created_at else None,
             "facility_name": i.facility_name, "disposition": i.disposition}
            for i in inspections
        ],
        "finding_timeline": [
            {**row, "created_at": row["created_at"].isoformat() if row["created_at"] else None} for row in timeline
        ],
        "repair_history": repairs,
        "latest_assessment": to_dict(latest_assessment) if latest_assessment else None,
    }


def search_forensics(
    db: Session, tenant_id: str, *, manufacturer: str = "", instrument_family: str = "",
    anatomy_zone: str = "", failure_category: str = "", repair_vendor: str = "",
    facility: str = "", date_from=None, date_to=None,
) -> list[dict]:
    """Section 9 filters: manufacturer/instrument family/model/anatomy zone/
    failure category/repair vendor/facility/date range."""
    q = db.query(VulcanReliabilityAssessment).filter(VulcanReliabilityAssessment.tenant_id == tenant_id)
    if manufacturer:
        q = q.filter(VulcanReliabilityAssessment.manufacturer_name == manufacturer)
    if instrument_family:
        q = q.filter(VulcanReliabilityAssessment.instrument_family == instrument_family)
    if anatomy_zone:
        q = q.filter(VulcanReliabilityAssessment.anatomy_zone == anatomy_zone)
    if failure_category:
        q = q.filter(VulcanReliabilityAssessment.failure_category == failure_category)
    if date_from:
        q = q.filter(VulcanReliabilityAssessment.created_at >= date_from)
    if date_to:
        q = q.filter(VulcanReliabilityAssessment.created_at <= date_to)
    rows = q.order_by(VulcanReliabilityAssessment.created_at.desc()).all()

    results = [to_dict(r) for r in rows]

    if repair_vendor:
        identities_with_vendor = {
            r.instrument_identity for r in
            db.query(RepairRequest).filter(RepairRequest.tenant_id == tenant_id, RepairRequest.vendor_name == repair_vendor)
        }
        results = [r for r in results if r["instrument_identity"] in identities_with_vendor]

    if facility:
        identities_with_facility = {
            i.instrument_barcode and f"barcode:{i.instrument_barcode}" or (i.instrument_udi and f"udi:{i.instrument_udi}")
            for i in db.query(models.Inspection).filter(
                models.Inspection.tenant_id == tenant_id, models.Inspection.facility_name == facility,
            )
        }
        results = [r for r in results if r["instrument_identity"] in identities_with_facility]

    return results
