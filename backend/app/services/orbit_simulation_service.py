"""v4.5 — Project Orbit, Section 9: Readiness Simulation.

The brief asks for this capability "using Project Helix." A repository-
wide, case-insensitive search for "helix" before writing this file
returned zero matches anywhere in this codebase — no such system exists.
Rather than fabricate an integration with a system that was never built,
this module implements the readiness-simulation capability as new code,
extending the case-scoped pattern Sentinel's single-inspection
`simulation_engine_service.py` already established (`generate_scenarios`,
`project_workflow_impact`) up to case/OR scope. See
`docs/orbit/readiness-engine.md` for the full disambiguation note.

Every projection here is a transparent, deterministic recomputation over
the case's real current-state rows (never a black-box model) — the same
"decision support only" posture every other module in this codebase
takes with a hypothetical.
"""
from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.orbit_readiness import (
    DISCLAIMER,
    SCENARIO_CASE_TIME_SHIFT,
    SCENARIO_INSTRUMENT_UNAVAILABLE,
    SCENARIO_VENDOR_TRAY_DELAYED,
    ReadinessSimulationRun,
)
from app.services import or_connect_service


def _persist(db: Session, tenant_id: str, case_id: int, scenario_type: str, params: dict, impact: dict, rationale: str) -> dict:
    run = ReadinessSimulationRun(
        tenant_id=tenant_id, case_id=case_id, scenario_type=scenario_type,
        scenario_params_json=json.dumps(params), projected_impact_json=json.dumps(impact), rationale=rationale,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {
        "id": run.id, "case_id": case_id, "scenario_type": scenario_type, "params": params, "projected_impact": impact,
        "rationale": rationale, "human_review_required": True, "disclaimer": DISCLAIMER,
    }


def simulate_case_time_shift(db: Session, tenant_id: str, case_id: int, *, hours_shift: float) -> dict:
    """"What if this case starts N hours earlier/later?" — recomputes
    whether currently-pending vendor trays/loaner equipment would still
    arrive before the (hypothetical) new scheduled start, using each
    item's real current status only; no arrival time is fabricated for
    an item that hasn't shipped."""
    from app.models.or_connect import TRAY_RECEIVED, TRAY_RETURNED, VendorTray
    from app.models.orbit_readiness import LoanerEquipment

    case = or_connect_service.get_case_or_404(db, tenant_id, case_id)
    new_start = case.scheduled_start + timedelta(hours=hours_shift)

    trays = db.query(VendorTray).filter(VendorTray.tenant_id == tenant_id, VendorTray.case_id == case_id).all()
    equipment = db.query(LoanerEquipment).filter(LoanerEquipment.tenant_id == tenant_id, LoanerEquipment.case_id == case_id).all()

    at_risk_trays = [t.tray_name for t in trays if t.status not in (TRAY_RECEIVED, TRAY_RETURNED)]
    at_risk_equipment = [e.equipment_name for e in equipment if e.status not in ("received", "returned")]

    hours_available = (new_start - case.scheduled_start).total_seconds() / 3600.0
    impact = {
        "original_scheduled_start": case.scheduled_start.isoformat(), "hypothetical_scheduled_start": new_start.isoformat(),
        "hours_shift": hours_shift, "at_risk_vendor_trays": at_risk_trays, "at_risk_loaner_equipment": at_risk_equipment,
        "still_at_risk": bool(at_risk_trays or at_risk_equipment) and hours_available <= 0,
    }
    rationale = (
        f"Shifting {case.case_ref} by {hours_shift}h "
        + (f"gives {abs(hours_shift):.1f} more hours for {len(at_risk_trays) + len(at_risk_equipment)} pending item(s) to arrive."
           if hours_shift > 0 else f"removes {abs(hours_shift):.1f} hours of buffer for {len(at_risk_trays) + len(at_risk_equipment)} pending item(s).")
        if (at_risk_trays or at_risk_equipment) else "No vendor trays or loaner equipment are currently pending, so the time shift has no readiness impact."
    )
    return _persist(db, tenant_id, case_id, SCENARIO_CASE_TIME_SHIFT, {"hours_shift": hours_shift}, impact, rationale)


def simulate_instrument_unavailable(db: Session, tenant_id: str, case_id: int, *, inspection_id: int) -> dict:
    """"What if a required instrument is unavailable?" — reports the real
    ready/not-ready counts behind the Case Readiness Score's instrument-
    readiness factor and how they'd shift if this one inspection were
    excluded, without fabricating a precise new overall score (that
    requires actually excluding the instrument and recomputing for real)."""
    from app.db import models
    from app.services.readiness_engine import READY, READY_WITH_SUPERVISOR_APPROVAL, compute_readiness

    case = or_connect_service.get_case_or_404(db, tenant_id, case_id)
    insp = db.query(models.Inspection).filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id).first()
    if insp is None:
        raise or_connect_service.CaseNotFoundError(f"Inspection {inspection_id} not found for tenant {tenant_id}.")

    inspections = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id, models.Inspection.case_id == case_id).all()
    ready_now = sum(1 for i in inspections if compute_readiness(db, tenant_id, i, confirmed=False)["status"] in (READY, READY_WITH_SUPERVISOR_APPROVAL))
    was_ready = insp.id in [i.id for i in inspections if compute_readiness(db, tenant_id, i, confirmed=False)["status"] in (READY, READY_WITH_SUPERVISOR_APPROVAL)]

    impact = {
        "removed_inspection_id": inspection_id, "instrument_identity": insp.instrument_type,
        "instruments_ready_before": ready_now, "instruments_ready_after": ready_now - 1 if was_ready else ready_now,
        "instruments_total": len(inspections),
        "note": "Run the Surgical Readiness Engine again after actually excluding this instrument for an exact recomputed overall score.",
    }
    rationale = (
        f"Inspection #{inspection_id} ({insp.instrument_type}) is currently "
        + ("counted as ready" if was_ready else "not currently ready")
        + f" toward {case.case_ref}'s instrument-readiness factor ({ready_now} of {len(inspections)} instruments ready)."
    )
    return _persist(db, tenant_id, case_id, SCENARIO_INSTRUMENT_UNAVAILABLE, {"inspection_id": inspection_id}, impact, rationale)


def simulate_vendor_tray_delayed(db: Session, tenant_id: str, case_id: int, *, tray_id: int, delay_hours: float) -> dict:
    """"What if a vendor tray is delayed?" — projects whether the delay
    pushes the tray's arrival past the case's scheduled start, using the
    tray's real current state (shipped_at if known, else "not yet shipped")."""
    from app.models.or_connect import VendorTray

    case = or_connect_service.get_case_or_404(db, tenant_id, case_id)
    tray = db.query(VendorTray).filter(VendorTray.id == tray_id, VendorTray.tenant_id == tenant_id).first()
    if tray is None:
        raise or_connect_service.CaseNotFoundError(f"Vendor tray {tray_id} not found for tenant {tenant_id}.")

    scheduled_start = case.scheduled_start
    if tray.shipped_at is not None:
        projected_arrival = tray.shipped_at + timedelta(hours=delay_hours)
        misses_case = projected_arrival > scheduled_start
    else:
        projected_arrival = None
        misses_case = None  # not yet shipped — arrival can't be projected without fabricating a ship date

    impact = {
        "tray_name": tray.tray_name, "delay_hours": delay_hours,
        "projected_arrival": projected_arrival.isoformat() if projected_arrival else None,
        "misses_case_start": misses_case,
    }
    rationale = (
        f"{tray.tray_name} would arrive at {projected_arrival.isoformat()}, "
        + ("after" if misses_case else "before") + f" {case.case_ref}'s scheduled start."
        if projected_arrival else
        f"{tray.tray_name} has not yet shipped — a delay cannot be projected onto an unknown ship date without fabricating one."
    )
    return _persist(db, tenant_id, case_id, SCENARIO_VENDOR_TRAY_DELAYED, {"tray_id": tray_id, "delay_hours": delay_hours}, impact, rationale)


def list_simulation_runs(db: Session, tenant_id: str, case_id: int) -> list[dict]:
    rows = (
        db.query(ReadinessSimulationRun)
        .filter(ReadinessSimulationRun.tenant_id == tenant_id, ReadinessSimulationRun.case_id == case_id)
        .order_by(ReadinessSimulationRun.id.desc())
        .all()
    )
    return [
        {
            "id": r.id, "scenario_type": r.scenario_type, "created_at": r.created_at.isoformat(),
            "params": json.loads(r.scenario_params_json), "projected_impact": json.loads(r.projected_impact_json),
            "rationale": r.rationale,
        }
        for r in rows
    ]
