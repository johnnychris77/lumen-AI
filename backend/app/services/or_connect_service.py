"""v2.8 — LumenAI OR Connect: Perioperative Coordination Engine (Project Symphony).

Case Coordination Engine, Case Readiness Score, Intelligent Readiness
Timeline, Operational Risk Detection, Stakeholder Notifications, Case
Intelligence Dashboard, Clinical Engineering Integration, and Executive OR
Coordination Dashboard.

Reuses existing engines rather than re-deriving their logic: readiness/
disposition state comes from `readiness_engine`/`disposition_engine` (the
same engines the Clinical Simulation Engine uses), never a second scoring
pass. Vendor-portal-specific views/actions live in
`or_connect_vendor_service.py`, which enforces real per-vendor row scoping.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import models
from app.models.or_connect import (
    DISCLAIMER,
    REPAIR_IN_PROGRESS,
    REPAIR_PENDING,
    RISK_BASELINE_MISSING,
    RISK_CRITICAL_FINDING_UNRESOLVED,
    RISK_INSPECTION_OVERDUE,
    RISK_REPAIR_INCOMPLETE,
    RISK_SUPERVISOR_REVIEW_PENDING,
    RISK_VENDOR_TRAY_NOT_RECEIVED,
    ROLE_CLINICAL_ENGINEERING,
    ROLE_SPD,
    ROLE_SUPPLY_CHAIN,
    ROLE_SURGEON,
    ROLE_VENDOR_REP,
    TRAY_RECEIVED,
    TRAY_REQUESTED,
    TRAY_RETURNED,
    TRAY_SHIPPED,
    CaseNotification,
    CaseReadinessScoreRecord,
    CaseRiskAlert,
    RepairRequest,
    SurgicalCase,
    VendorTray,
)
from app.models.supervisor_review import SupervisorReview
from app.services.pre_sterilization_command_center_service import _instrument_identity
from app.services.readiness_engine import (
    READY,
    READY_WITH_SUPERVISOR_APPROVAL,
    compute_readiness,
)

_OVERDUE_MINUTES_THRESHOLD = 480  # 8h, same threshold as workflow_notification_service
_TRAY_AT_RISK_HOURS = 24

_RISK_TO_ROLES = {
    RISK_VENDOR_TRAY_NOT_RECEIVED: [ROLE_VENDOR_REP, ROLE_SUPPLY_CHAIN],
    RISK_INSPECTION_OVERDUE: [ROLE_SPD],
    RISK_BASELINE_MISSING: [ROLE_SPD],
    RISK_REPAIR_INCOMPLETE: [ROLE_CLINICAL_ENGINEERING],
    RISK_CRITICAL_FINDING_UNRESOLVED: [ROLE_SURGEON, ROLE_SPD],
    RISK_SUPERVISOR_REVIEW_PENDING: [ROLE_SPD],
}


class CaseNotFoundError(Exception):
    pass


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def get_case_or_404(db: Session, tenant_id: str, case_id: int) -> SurgicalCase:
    case = (
        db.query(SurgicalCase)
        .filter(SurgicalCase.id == case_id, SurgicalCase.tenant_id == tenant_id)
        .first()
    )
    if case is None:
        raise CaseNotFoundError(f"Surgical case {case_id} not found for tenant {tenant_id}.")
    return case


def _case_inspections(db: Session, tenant_id: str, case_id: int) -> list:
    return (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.case_id == case_id)
        .all()
    )


def _case_trays(db: Session, tenant_id: str, case_id: int) -> list[VendorTray]:
    return (
        db.query(VendorTray)
        .filter(VendorTray.tenant_id == tenant_id, VendorTray.case_id == case_id)
        .all()
    )


def _case_repairs(db: Session, tenant_id: str, case_id: int) -> list[RepairRequest]:
    return (
        db.query(RepairRequest)
        .filter(RepairRequest.tenant_id == tenant_id, RepairRequest.case_id == case_id)
        .all()
    )


# ---------------------------------------------------------------------------
# Section 1 — Case Coordination Engine
# ---------------------------------------------------------------------------


def create_case(
    db: Session, tenant_id: str, *, procedure: str, scheduled_start: datetime, service_line: str = "",
    surgeon: str = "", facility_name: str = "", operating_room: str = "", vendor_name: str = "", notes: str = "",
) -> SurgicalCase:
    case_ref = f"CASE-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
    case = SurgicalCase(
        tenant_id=tenant_id, case_ref=case_ref, procedure=procedure, service_line=service_line,
        surgeon=surgeon, facility_name=facility_name, operating_room=operating_room,
        scheduled_start=scheduled_start, vendor_name=vendor_name, notes=notes,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def list_cases(db: Session, tenant_id: str, *, target_date: date | None = None) -> list[SurgicalCase]:
    q = db.query(SurgicalCase).filter(SurgicalCase.tenant_id == tenant_id)
    if target_date is not None:
        start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        q = q.filter(SurgicalCase.scheduled_start >= start, SurgicalCase.scheduled_start < end)
    return q.order_by(SurgicalCase.scheduled_start.asc()).all()


def link_inspection_to_case(db: Session, tenant_id: str, case_id: int, inspection_id: int):
    get_case_or_404(db, tenant_id, case_id)
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        raise CaseNotFoundError(f"Inspection {inspection_id} not found for tenant {tenant_id}.")
    insp.case_id = case_id
    db.commit()
    db.refresh(insp)
    return insp


def add_vendor_tray(
    db: Session, tenant_id: str, case_id: int, *, tray_name: str, vendor_name: str = "",
    tray_label: str = "", is_vendor_tray: bool = True,
) -> VendorTray:
    get_case_or_404(db, tenant_id, case_id)
    tray = VendorTray(
        tenant_id=tenant_id, case_id=case_id, tray_name=tray_name, vendor_name=vendor_name,
        tray_label=tray_label, is_vendor_tray=is_vendor_tray, requested_at=datetime.now(timezone.utc),
    )
    db.add(tray)
    db.commit()
    db.refresh(tray)
    return tray


_TRAY_STATUS_TIMESTAMP_FIELD = {
    TRAY_SHIPPED: "shipped_at", TRAY_RECEIVED: "received_at", TRAY_RETURNED: "returned_at",
}


def update_tray_status(db: Session, tenant_id: str, tray_id: int, *, status: str) -> VendorTray:
    tray = db.query(VendorTray).filter(VendorTray.id == tray_id, VendorTray.tenant_id == tenant_id).first()
    if tray is None:
        raise CaseNotFoundError(f"Vendor tray {tray_id} not found for tenant {tenant_id}.")
    tray.status = status
    field = _TRAY_STATUS_TIMESTAMP_FIELD.get(status)
    if field is not None:
        setattr(tray, field, datetime.now(timezone.utc))
    db.commit()
    db.refresh(tray)
    return tray


def case_detail(db: Session, tenant_id: str, case_id: int) -> dict:
    """Section 1 — the full case view: identity, trays, inspections, and
    derived status (never duplicated storage of what an Inspection already
    tracks)."""
    case = get_case_or_404(db, tenant_id, case_id)
    inspections = _case_inspections(db, tenant_id, case_id)
    trays = _case_trays(db, tenant_id, case_id)
    repairs = _case_repairs(db, tenant_id, case_id)

    vendor_trays = [t for t in trays if t.vendor_name]
    hospital_trays = [t for t in trays if not t.vendor_name]

    digital_twins = sorted({_instrument_identity(i) for i in inspections})

    scored = [i for i in inspections if i.score_status in ("scored", "scored_after_override")]
    inspection_status = (
        "no_inspections_linked" if not inspections
        else "complete" if len(scored) == len(inspections)
        else f"{len(scored)}_of_{len(inspections)}_complete"
    )

    reviews_by_inspection = {
        r.inspection_id: r
        for r in (
            db.query(SupervisorReview)
            .filter(SupervisorReview.inspection_id.in_([i.id for i in inspections]))
            .all()
        )
    } if inspections else {}
    readiness_statuses = [
        compute_readiness(db, tenant_id, i, confirmed=i.id in reviews_by_inspection)["status"]
        for i in inspections
    ]
    clinical_readiness = (
        "not_assessed" if not readiness_statuses
        else "ready" if all(s in (READY, READY_WITH_SUPERVISOR_APPROVAL) for s in readiness_statuses)
        else "not_ready"
    )

    open_repairs = [r for r in repairs if r.status in (REPAIR_PENDING, REPAIR_IN_PROGRESS)]
    repair_status = "no_repairs" if not repairs else "open" if open_repairs else "resolved"

    return {
        **_row_to_dict(case),
        "vendor_trays": [_row_to_dict(t) for t in vendor_trays],
        "hospital_trays": [_row_to_dict(t) for t in hospital_trays],
        "digital_twins": digital_twins,
        "inspection_ids": [i.id for i in inspections],
        "inspection_status": inspection_status,
        "clinical_readiness": clinical_readiness,
        "repair_status": repair_status,
        "supervisor_approval": "approved" if case.supervisor_approved else "pending",
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Section 2 — Case Readiness Score
# ---------------------------------------------------------------------------


def _ratio(numerator: int, denominator: int) -> float:
    """1.0 (not blocking) when nothing of this kind is required yet."""
    return 1.0 if denominator == 0 else numerator / denominator


def compute_case_readiness_score(db: Session, tenant_id: str, case_id: int) -> dict:
    case = get_case_or_404(db, tenant_id, case_id)
    inspections = _case_inspections(db, tenant_id, case_id)
    trays = _case_trays(db, tenant_id, case_id)
    repairs = _case_repairs(db, tenant_id, case_id)

    vendor_trays = [t for t in trays if t.vendor_name]
    hospital_trays = [t for t in trays if not t.vendor_name]

    reviews_by_inspection = {
        r.inspection_id: r
        for r in (
            db.query(SupervisorReview)
            .filter(SupervisorReview.inspection_id.in_([i.id for i in inspections]))
            .all()
        )
    } if inspections else {}
    readiness = [
        compute_readiness(db, tenant_id, i, confirmed=i.id in reviews_by_inspection) for i in inspections
    ]

    factors = {
        "instrument_readiness": (
            25, _ratio(sum(1 for r in readiness if r["status"] in (READY, READY_WITH_SUPERVISOR_APPROVAL)), len(readiness)),
        ),
        "vendor_tray_arrival": (
            15, _ratio(sum(1 for t in vendor_trays if t.status in (TRAY_RECEIVED, TRAY_RETURNED)), len(vendor_trays)),
        ),
        "inspection_completion": (
            15, _ratio(sum(1 for i in inspections if i.score_status in ("scored", "scored_after_override")), len(inspections)),
        ),
        "coverage_completion": (
            10,
            (
                sum(i.coverage_pct for i in inspections if i.coverage_pct is not None)
                / (100.0 * sum(1 for i in inspections if i.coverage_pct is not None))
            ) if any(i.coverage_pct is not None for i in inspections) else 1.0,
        ),
        "baseline_verification": (
            10, _ratio(sum(1 for i in inspections if i.baseline_status == "approved"), len(inspections)),
        ),
        "repair_completion": (
            10, _ratio(sum(1 for r in repairs if r.status in ("returned", "replaced")), len(repairs)),
        ),
        "supervisor_approvals": (
            10, 1.0 if case.supervisor_approved else _ratio(len(reviews_by_inspection), len(inspections)),
        ),
        "specialty_equipment_available": (
            5, _ratio(sum(1 for t in hospital_trays if t.status in (TRAY_RECEIVED, TRAY_RETURNED)), len(hospital_trays)),
        ),
    }

    score = round(sum(weight * value for weight, value in factors.values()))

    rationale_parts = []
    for name, (weight, value) in factors.items():
        if value < 1.0:
            rationale_parts.append(f"{name.replace('_', ' ')} is incomplete ({round(value * 100)}%, worth {weight} pts).")
    rationale = " ".join(rationale_parts) or "All weighted readiness factors are fully satisfied."

    factor_breakdown = {
        name: {"weight": weight, "value": round(value, 3), "points": round(weight * value, 2)}
        for name, (weight, value) in factors.items()
    }

    record = CaseReadinessScoreRecord(
        tenant_id=tenant_id, case_id=case_id, score=score,
        factors_json=json.dumps(factor_breakdown), rationale=rationale,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    result = _row_to_dict(record)
    result["factors"] = factor_breakdown
    return result


# ---------------------------------------------------------------------------
# Section 3 — Intelligent Readiness Timeline
# ---------------------------------------------------------------------------


def build_case_timeline(db: Session, tenant_id: str, case_id: int) -> dict:
    case = get_case_or_404(db, tenant_id, case_id)
    inspections = _case_inspections(db, tenant_id, case_id)
    trays = _case_trays(db, tenant_id, case_id)
    vendor_trays = [t for t in trays if t.vendor_name]

    now = datetime.now(timezone.utc)
    scheduled_start = case.scheduled_start
    if scheduled_start.tzinfo is None:
        scheduled_start = scheduled_start.replace(tzinfo=timezone.utc)
    past_due = now > scheduled_start

    vendor_confirmed = (not vendor_trays) or any(t.status != TRAY_REQUESTED for t in vendor_trays)
    vendor_confirmed_at = min(
        (t.shipped_at for t in vendor_trays if t.shipped_at), default=None,
    )

    all_trays_received = (not trays) or all(t.status in (TRAY_RECEIVED, TRAY_RETURNED) for t in trays)
    tray_received_at = max((t.received_at for t in trays if t.received_at), default=None)

    inspection_complete = bool(inspections) and all(
        i.score_status in ("scored", "scored_after_override") for i in inspections
    )
    inspection_complete_at = max(
        (i.inference_timestamp for i in inspections if i.inference_timestamp), default=None,
    )

    packaging_ready = bool(inspections) and all(
        compute_readiness(db, tenant_id, i, confirmed=case.supervisor_approved)["status"]
        in (READY, READY_WITH_SUPERVISOR_APPROVAL)
        for i in inspections
    )
    ready_for_or = packaging_ready and all_trays_received and case.supervisor_approved

    steps = [
        {"step": "Case Scheduled", "completed": True, "timestamp": case.created_at.isoformat()},
        {"step": "Vendor Confirmed", "completed": vendor_confirmed,
         "timestamp": vendor_confirmed_at.isoformat() if vendor_confirmed_at else None},
        {"step": "Tray Received", "completed": all_trays_received,
         "timestamp": tray_received_at.isoformat() if tray_received_at else None},
        {"step": "Inspection Complete", "completed": inspection_complete,
         "timestamp": inspection_complete_at.isoformat() if inspection_complete_at else None},
        {"step": "Supervisor Approved", "completed": case.supervisor_approved,
         "timestamp": case.supervisor_approved_at.isoformat() if case.supervisor_approved_at else None},
        {"step": "Packaging", "completed": packaging_ready, "timestamp": None},
        {"step": "Ready for OR", "completed": ready_for_or, "timestamp": None},
    ]

    blockers = [
        {"step": s["step"], "reason": f"{s['step']} not yet complete.", "delayed": past_due}
        for s in steps if not s["completed"]
    ]

    return {
        "case_id": case_id, "case_ref": case.case_ref, "steps": steps, "blockers": blockers,
        "past_due": past_due,
        "note": (
            "Steps only show a timestamp when a real, independently-timed record exists — "
            "no timestamp is fabricated for a step that hasn't actually happened."
        ),
    }


# ---------------------------------------------------------------------------
# Section 4 — Operational Risk Detection
# ---------------------------------------------------------------------------


def _already_alerted(db: Session, tenant_id: str, case_id: int, risk_type: str) -> bool:
    return (
        db.query(CaseRiskAlert.id)
        .filter(
            CaseRiskAlert.tenant_id == tenant_id, CaseRiskAlert.case_id == case_id,
            CaseRiskAlert.risk_type == risk_type, CaseRiskAlert.resolved_at.is_(None),
        )
        .first()
        is not None
    )


def detect_operational_risks(db: Session, tenant_id: str, case_id: int) -> list[dict]:
    case = get_case_or_404(db, tenant_id, case_id)
    inspections = _case_inspections(db, tenant_id, case_id)
    trays = _case_trays(db, tenant_id, case_id)
    repairs = _case_repairs(db, tenant_id, case_id)
    vendor_trays = [t for t in trays if t.vendor_name]

    now = datetime.now(timezone.utc)
    scheduled_start = case.scheduled_start
    if scheduled_start.tzinfo is None:
        scheduled_start = scheduled_start.replace(tzinfo=timezone.utc)
    hours_to_case = (scheduled_start - now).total_seconds() / 3600.0

    def _severity_by_urgency() -> str:
        if hours_to_case <= 0:
            return "critical"
        if hours_to_case <= 6:
            return "critical"
        if hours_to_case <= _TRAY_AT_RISK_HOURS:
            return "high"
        return "medium"

    created: list[CaseRiskAlert] = []

    def _emit(risk_type: str, severity: str, message: str) -> None:
        if not _already_alerted(db, tenant_id, case_id, risk_type):
            row = CaseRiskAlert(tenant_id=tenant_id, case_id=case_id, risk_type=risk_type, severity=severity, message=message)
            db.add(row)
            created.append(row)

    if any(t.status in (TRAY_REQUESTED, TRAY_SHIPPED) for t in vendor_trays) and hours_to_case <= _TRAY_AT_RISK_HOURS:
        pending = [t for t in vendor_trays if t.status in (TRAY_REQUESTED, TRAY_SHIPPED)]
        _emit(
            RISK_VENDOR_TRAY_NOT_RECEIVED, _severity_by_urgency(),
            f"{len(pending)} vendor tray(s) not yet received for {case.case_ref}, case scheduled in "
            f"{max(0, round(hours_to_case, 1))}h.",
        )

    for insp in inspections:
        if insp.score_status not in ("scored", "scored_after_override"):
            age_minutes = (now - insp.created_at).total_seconds() / 60.0 if insp.created_at else 0
            if age_minutes >= _OVERDUE_MINUTES_THRESHOLD:
                _emit(
                    RISK_INSPECTION_OVERDUE, _severity_by_urgency(),
                    f"Inspection #{insp.id} for {case.case_ref} has been pending analysis for over "
                    f"{_OVERDUE_MINUTES_THRESHOLD // 60}h.",
                )
        if insp.baseline_status != "approved":
            _emit(
                RISK_BASELINE_MISSING, "medium",
                f"Inspection #{insp.id} for {case.case_ref} has no approved baseline "
                f"(status: {insp.baseline_status or 'not_checked'}).",
            )

    for repair in repairs:
        if repair.status in (REPAIR_PENDING, REPAIR_IN_PROGRESS):
            overdue = repair.expected_return_date is not None and repair.expected_return_date > scheduled_start
            _emit(
                RISK_REPAIR_INCOMPLETE, "critical" if overdue else "medium",
                f"Repair request #{repair.id} for {case.case_ref} is still {repair.status}"
                + (", expected return after the case's scheduled start." if overdue else "."),
            )

    reviews_by_inspection = {
        r.inspection_id for r in (
            db.query(SupervisorReview).filter(SupervisorReview.inspection_id.in_([i.id for i in inspections])).all()
        )
    } if inspections else set()

    for insp in inspections:
        readiness = compute_readiness(db, tenant_id, insp, confirmed=insp.id in reviews_by_inspection)
        if readiness["is_critical_finding"] and insp.id not in reviews_by_inspection:
            _emit(
                RISK_CRITICAL_FINDING_UNRESOLVED, "critical",
                f"Inspection #{insp.id} for {case.case_ref} has an unresolved critical finding.",
            )
        if insp.supervisor_review_required and insp.id not in reviews_by_inspection:
            _emit(
                RISK_SUPERVISOR_REVIEW_PENDING, _severity_by_urgency(),
                f"Inspection #{insp.id} for {case.case_ref} is awaiting supervisor review.",
            )

    db.commit()
    for row in created:
        db.refresh(row)

    all_open = (
        db.query(CaseRiskAlert)
        .filter(CaseRiskAlert.tenant_id == tenant_id, CaseRiskAlert.case_id == case_id, CaseRiskAlert.resolved_at.is_(None))
        .order_by(CaseRiskAlert.id.desc())
        .all()
    )
    return [_row_to_dict(r) for r in all_open]


# ---------------------------------------------------------------------------
# Section 5 — Automatic Stakeholder Notifications
# ---------------------------------------------------------------------------


def _already_notified(db: Session, tenant_id: str, case_id: int, notification_type: str, recipient_role: str) -> bool:
    return (
        db.query(CaseNotification.id)
        .filter(
            CaseNotification.tenant_id == tenant_id, CaseNotification.case_id == case_id,
            CaseNotification.notification_type == notification_type, CaseNotification.recipient_role == recipient_role,
        )
        .first()
        is not None
    )


def generate_stakeholder_notifications(db: Session, tenant_id: str, case_id: int) -> list[dict]:
    risks = detect_operational_risks(db, tenant_id, case_id)
    created = []
    for risk in risks:
        for role in _RISK_TO_ROLES.get(risk["risk_type"], [ROLE_SPD]):
            if not _already_notified(db, tenant_id, case_id, risk["risk_type"], role):
                row = CaseNotification(
                    tenant_id=tenant_id, case_id=case_id, notification_type=risk["risk_type"],
                    recipient_role=role, message=risk["message"],
                )
                db.add(row)
                created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return [_row_to_dict(r) for r in created]


def list_case_notifications(db: Session, tenant_id: str, *, recipient_role: str, unread_only: bool = False) -> list[dict]:
    q = db.query(CaseNotification).filter(
        CaseNotification.tenant_id == tenant_id, CaseNotification.recipient_role == recipient_role,
    )
    if unread_only:
        q = q.filter(CaseNotification.read.is_(False))
    return [_row_to_dict(r) for r in q.order_by(CaseNotification.id.desc()).all()]


def mark_notification_read(db: Session, tenant_id: str, notification_id: int) -> dict | None:
    row = (
        db.query(CaseNotification)
        .filter(CaseNotification.tenant_id == tenant_id, CaseNotification.id == notification_id)
        .first()
    )
    if row is None:
        return None
    row.read = True
    row.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


# ---------------------------------------------------------------------------
# Section 6 — Case Intelligence Dashboard
# ---------------------------------------------------------------------------


def dashboard_summary(db: Session, tenant_id: str, *, target_date: date | None = None) -> dict:
    target_date = target_date or datetime.now(timezone.utc).date()
    cases = list_cases(db, tenant_id, target_date=target_date)

    case_summaries = []
    high_risk_cases = []
    projected_delays = []
    tray_status_counts: dict[str, int] = {}
    total_inspections = 0
    scored_inspections = 0

    for case in cases:
        readiness = compute_case_readiness_score(db, tenant_id, case.id)
        risks = (
            db.query(CaseRiskAlert)
            .filter(CaseRiskAlert.tenant_id == tenant_id, CaseRiskAlert.case_id == case.id, CaseRiskAlert.resolved_at.is_(None))
            .all()
        )
        trays = _case_trays(db, tenant_id, case.id)
        inspections = _case_inspections(db, tenant_id, case.id)
        total_inspections += len(inspections)
        scored_inspections += sum(1 for i in inspections if i.score_status in ("scored", "scored_after_override"))

        for t in trays:
            tray_status_counts[t.status] = tray_status_counts.get(t.status, 0) + 1

        summary = {
            "case_id": case.id, "case_ref": case.case_ref, "procedure": case.procedure,
            "scheduled_start": case.scheduled_start.isoformat(), "readiness_score": readiness["score"],
            "open_risk_count": len(risks),
        }
        case_summaries.append(summary)

        if any(r.severity in ("high", "critical") for r in risks):
            high_risk_cases.append(summary)

        now = datetime.now(timezone.utc)
        scheduled_start = case.scheduled_start if case.scheduled_start.tzinfo else case.scheduled_start.replace(tzinfo=timezone.utc)
        if readiness["score"] < 70 and (scheduled_start - now).total_seconds() <= 24 * 3600:
            projected_delays.append(summary)

    return {
        "date": target_date.isoformat(),
        "total_cases": len(cases),
        "cases": case_summaries,
        "high_risk_cases": high_risk_cases,
        "vendor_tray_status": tray_status_counts,
        "inspection_completion_pct": round(100 * scored_inspections / total_inspections) if total_inspections else None,
        "outstanding_blockers": [
            _row_to_dict(r) for r in (
                db.query(CaseRiskAlert)
                .filter(
                    CaseRiskAlert.tenant_id == tenant_id, CaseRiskAlert.resolved_at.is_(None),
                    CaseRiskAlert.case_id.in_([c.id for c in cases]) if cases else False,
                )
                .all()
            )
        ] if cases else [],
        "projected_delays": projected_delays,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Section 8 — Clinical Engineering Integration
# ---------------------------------------------------------------------------


def create_repair_request(
    db: Session, tenant_id: str, *, inspection_id: int, case_id: int | None = None, vendor_name: str = "",
    repair_type: str = "", expected_return_date: datetime | None = None, notes: str = "",
) -> dict:
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        raise CaseNotFoundError(f"Inspection {inspection_id} not found for tenant {tenant_id}.")
    row = RepairRequest(
        tenant_id=tenant_id, case_id=case_id, inspection_id=inspection_id,
        instrument_identity=_instrument_identity(insp), vendor_name=vendor_name, repair_type=repair_type,
        expected_return_date=expected_return_date, notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def update_repair_request(
    db: Session, tenant_id: str, repair_id: int, *, status: str | None = None,
    actual_return_date: datetime | None = None, replacement_available: bool | None = None,
) -> dict:
    row = db.query(RepairRequest).filter(RepairRequest.id == repair_id, RepairRequest.tenant_id == tenant_id).first()
    if row is None:
        raise CaseNotFoundError(f"Repair request {repair_id} not found for tenant {tenant_id}.")
    if status is not None:
        row.status = status
    if actual_return_date is not None:
        row.actual_return_date = actual_return_date
    if replacement_available is not None:
        row.replacement_available = replacement_available
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


def clinical_engineering_summary(db: Session, tenant_id: str) -> dict:
    repairs = db.query(RepairRequest).filter(RepairRequest.tenant_id == tenant_id).order_by(RepairRequest.id.desc()).all()
    open_repairs = [r for r in repairs if r.status in (REPAIR_PENDING, REPAIR_IN_PROGRESS)]
    completed = [r for r in repairs if r.actual_return_date is not None]
    avg_turnaround_days = (
        round(sum((r.actual_return_date - r.created_at).days for r in completed) / len(completed), 1)
        if completed else None
    )
    return {
        "open_repairs": [_row_to_dict(r) for r in open_repairs],
        "total_repairs": len(repairs),
        "avg_turnaround_days": avg_turnaround_days,
        "replacement_available_count": sum(1 for r in repairs if r.replacement_available),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Section 9 — Executive OR Coordination Dashboard
# ---------------------------------------------------------------------------


def executive_dashboard(db: Session, tenant_id: str, *, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    score_rows = (
        db.query(CaseReadinessScoreRecord)
        .filter(CaseReadinessScoreRecord.tenant_id == tenant_id, CaseReadinessScoreRecord.created_at >= since)
        .all()
    )
    trend: dict[str, list[int]] = {}
    for r in score_rows:
        day_key = r.created_at.date().isoformat()
        trend.setdefault(day_key, []).append(r.score)
    readiness_trend = [
        {"date": d, "avg_score": round(sum(scores) / len(scores), 1)} for d, scores in sorted(trend.items())
    ]

    risk_rows = (
        db.query(CaseRiskAlert)
        .filter(CaseRiskAlert.tenant_id == tenant_id, CaseRiskAlert.created_at >= since)
        .all()
    )
    delay_causes: dict[str, int] = {}
    for r in risk_rows:
        delay_causes[r.risk_type] = delay_causes.get(r.risk_type, 0) + 1

    tray_rows = (
        db.query(VendorTray)
        .filter(VendorTray.tenant_id == tenant_id, VendorTray.created_at >= since, VendorTray.vendor_name != "")
        .all()
    )
    vendor_performance: dict[str, dict[str, int]] = {}
    for t in tray_rows:
        v = vendor_performance.setdefault(t.vendor_name, {"total": 0, "received": 0})
        v["total"] += 1
        if t.status in (TRAY_RECEIVED, TRAY_RETURNED):
            v["received"] += 1

    case_rows = db.query(SurgicalCase).filter(SurgicalCase.tenant_id == tenant_id, SurgicalCase.created_at >= since).all()
    case_ids = [c.id for c in case_rows]
    inspection_rows = (
        db.query(models.Inspection)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.case_id.in_(case_ids))
        .all()
    ) if case_ids else []
    turnaround_hours = [
        (i.inference_timestamp - i.created_at).total_seconds() / 3600
        for i in inspection_rows if i.inference_timestamp and i.created_at
    ]
    inspection_turnaround_hours = round(sum(turnaround_hours) / len(turnaround_hours), 2) if turnaround_hours else None

    repair_rows = (
        db.query(RepairRequest)
        .filter(RepairRequest.tenant_id == tenant_id, RepairRequest.created_at >= since)
        .all()
    )
    open_repair_case_ids = {r.case_id for r in repair_rows if r.status in (REPAIR_PENDING, REPAIR_IN_PROGRESS) and r.case_id}
    completed_repairs = [r for r in repair_rows if r.actual_return_date is not None]
    repair_turnaround_days = (
        round(sum((r.actual_return_date - r.created_at).days for r in completed_repairs) / len(completed_repairs), 1)
        if completed_repairs else None
    )

    quality_alerts = sum(1 for r in risk_rows if r.risk_type == RISK_CRITICAL_FINDING_UNRESOLVED)

    bottleneck_counter: dict[str, int] = {}
    case_by_id = {c.id: c for c in case_rows}
    for r in risk_rows:
        case = case_by_id.get(r.case_id)
        if case is not None and case.service_line:
            bottleneck_counter[case.service_line] = bottleneck_counter.get(case.service_line, 0) + 1
    operational_bottlenecks = sorted(
        [{"service_line": k, "risk_count": v} for k, v in bottleneck_counter.items()],
        key=lambda x: x["risk_count"], reverse=True,
    )[:10]

    return {
        "window_days": days,
        "case_readiness_trend": readiness_trend,
        "delay_causes": delay_causes,
        "vendor_performance": {
            k: {"total": v["total"], "on_time_pct": round(100 * v["received"] / v["total"]) if v["total"] else None}
            for k, v in vendor_performance.items()
        },
        "inspection_turnaround_hours": inspection_turnaround_hours,
        "repair_impact": {
            "cases_with_open_repairs": len(open_repair_case_ids),
            "avg_repair_turnaround_days": repair_turnaround_days,
        },
        "quality_alerts": quality_alerts,
        "operational_bottlenecks": operational_bottlenecks,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
