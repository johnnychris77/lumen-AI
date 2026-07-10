"""v2.9 — LumenAI Quality (Project Guardian), Section 4: Intelligent Event
Correlation.

Attempts to associate a quality event with the case, procedure, tray,
digital twin, inspection, technician, and supervisor already tracked
elsewhere in LumenAI. Shift, washer, and inspection-session correlation are
recorded honestly as untracked (`UNTRACKED_TARGETS`) — LumenAI does not
persist those as real entities today, and fabricating a match would violate
the same "never guess" principle `root_cause_service.py` already applies.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.baseline_library import BaselineLibraryEntry
from app.models.or_connect import SurgicalCase, VendorTray
from app.models.quality_guardian import (
    TARGET_CASE,
    TARGET_DIGITAL_TWIN,
    TARGET_INSPECTION,
    TARGET_INSPECTION_SESSION,
    TARGET_MANUFACTURER_BASELINE,
    TARGET_PROCEDURE,
    TARGET_SHIFT,
    TARGET_SUPERVISOR,
    TARGET_TECHNICIAN,
    TARGET_TRAY,
    TARGET_WASHER,
    EventCorrelation,
)
from app.models.supervisor_review import SupervisorReview
from app.models.workflow import InspectionAssignment
from app.services.pre_sterilization_command_center_service import _instrument_identity
from app.services.quality_event_service import QualityEventNotFoundError, _get_event

_CASE_TIME_WINDOW_HOURS = 48
_INSPECTION_TIME_WINDOW_HOURS = 72


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _upsert(db: Session, tenant_id: str, event_id: int, *, target_type: str, target_id: str = "",
            confidence: float = 0.0, tracked: bool = True, note: str = "") -> EventCorrelation:
    existing = (
        db.query(EventCorrelation)
        .filter(EventCorrelation.tenant_id == tenant_id, EventCorrelation.event_id == event_id,
                EventCorrelation.target_type == target_type)
        .first()
    )
    if existing is not None:
        existing.target_id = target_id
        existing.confidence = confidence
        existing.tracked = tracked
        existing.note = note
        return existing
    row = EventCorrelation(
        tenant_id=tenant_id, event_id=event_id, target_type=target_type, target_id=target_id,
        confidence=confidence, tracked=tracked, note=note,
    )
    db.add(row)
    return row


def correlate_event(db: Session, tenant_id: str, event_id: int) -> list[dict]:
    event = _get_event(db, tenant_id, event_id)
    rows: list[EventCorrelation] = []

    case = None
    if event.case_id is not None:
        case = db.query(SurgicalCase).filter(SurgicalCase.id == event.case_id, SurgicalCase.tenant_id == tenant_id).first()
        if case is not None:
            rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_CASE, target_id=str(case.id), confidence=1.0))
    else:
        window_start = event.event_date - timedelta(hours=_CASE_TIME_WINDOW_HOURS)
        window_end = event.event_date + timedelta(hours=_CASE_TIME_WINDOW_HOURS)
        candidate = (
            db.query(SurgicalCase)
            .filter(
                SurgicalCase.tenant_id == tenant_id, SurgicalCase.facility_name == event.facility_name,
                SurgicalCase.scheduled_start >= window_start, SurgicalCase.scheduled_start <= window_end,
            )
            .order_by(SurgicalCase.scheduled_start.asc())
            .first()
        )
        if candidate is not None:
            case = candidate
            rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_CASE, target_id=str(case.id), confidence=0.55,
                                 note="Matched by facility + scheduled time window, not an explicit case ID."))

    if case is not None:
        rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_PROCEDURE, target_id=case.procedure,
                             confidence=rows[-1].confidence if rows else 0.55))
        trays = db.query(VendorTray).filter(VendorTray.tenant_id == tenant_id, VendorTray.case_id == case.id).all()
        for tray in trays:
            rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_TRAY, target_id=str(tray.id), confidence=0.7))

    inspection = None
    if case is not None:
        inspection = (
            db.query(models.Inspection)
            .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.case_id == case.id)
            .order_by(models.Inspection.id.desc())
            .first()
        )
        if inspection is not None:
            rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_INSPECTION, target_id=str(inspection.id), confidence=0.85))
    if inspection is None and event.instrument_type_guess:
        window_start = event.event_date - timedelta(hours=_INSPECTION_TIME_WINDOW_HOURS)
        inspection = (
            db.query(models.Inspection)
            .filter(
                models.Inspection.tenant_id == tenant_id, models.Inspection.instrument_type == event.instrument_type_guess,
                models.Inspection.created_at >= window_start, models.Inspection.created_at <= event.event_date,
            )
            .order_by(models.Inspection.created_at.desc())
            .first()
        )
        if inspection is not None:
            rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_INSPECTION, target_id=str(inspection.id), confidence=0.45,
                                 note="Matched by instrument type + time window, not a linked case."))

    if inspection is not None:
        rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_DIGITAL_TWIN,
                             target_id=_instrument_identity(inspection), confidence=0.8))

        assignment = (
            db.query(InspectionAssignment)
            .filter(InspectionAssignment.inspection_id == inspection.id)
            .order_by(InspectionAssignment.id.desc())
            .first()
        )
        if assignment is not None:
            rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_TECHNICIAN, target_id=assignment.technician, confidence=0.8))
        elif inspection.technician:
            rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_TECHNICIAN, target_id=inspection.technician, confidence=0.6))

        review = (
            db.query(SupervisorReview)
            .filter(SupervisorReview.inspection_id == inspection.id)
            .order_by(SupervisorReview.id.desc())
            .first()
        )
        if review is not None:
            rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_SUPERVISOR, target_id=review.reviewer_name, confidence=0.75))

        baseline = (
            db.query(BaselineLibraryEntry)
            .filter(BaselineLibraryEntry.instrument_category == inspection.instrument_type)
            .order_by(BaselineLibraryEntry.id.desc())
            .first()
        )
        if baseline is not None:
            rows.append(_upsert(db, tenant_id, event_id, target_type=TARGET_MANUFACTURER_BASELINE,
                                 target_id=f"{baseline.manufacturer_name} {baseline.model_name}", confidence=0.5))

    for target_type in (TARGET_SHIFT, TARGET_WASHER, TARGET_INSPECTION_SESSION):
        rows.append(
            _upsert(
                db, tenant_id, event_id, target_type=target_type, target_id="", confidence=0.0, tracked=False,
                note=f"LumenAI does not persist a '{target_type.replace('_', ' ')}' entity today — this "
                     "correlation cannot honestly be attempted, only recorded as untracked.",
            ),
        )

    db.commit()
    for row in rows:
        db.refresh(row)

    return list_correlations(db, tenant_id, event_id)


def list_correlations(db: Session, tenant_id: str, event_id: int) -> list[dict]:
    rows = (
        db.query(EventCorrelation)
        .filter(EventCorrelation.tenant_id == tenant_id, EventCorrelation.event_id == event_id)
        .order_by(EventCorrelation.id.asc())
        .all()
    )
    return [_row_to_dict(r) for r in rows]


def confirm_correlation(db: Session, tenant_id: str, correlation_id: int, *, confirmed_by: str) -> dict:
    row = (
        db.query(EventCorrelation)
        .filter(EventCorrelation.id == correlation_id, EventCorrelation.tenant_id == tenant_id)
        .first()
    )
    if row is None:
        raise QualityEventNotFoundError(f"Correlation {correlation_id} not found for tenant {tenant_id}.")
    row.supervisor_confirmed = True
    row.confirmed_by = confirmed_by
    row.confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)
